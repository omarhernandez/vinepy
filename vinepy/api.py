#add check if requests is installed
import requests
import logging

from models import *
from endpoints import *
from errors import *


class API(object):
    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password
        self._endpoint = None
        self._session_id = None
        self.user = self.login() if self.username and self.password else DummyUser()

    def __getattr__(self, attr):
        if attr.startswith('__'):
            return object.__getattribute__(self, attr)
        self._endpoint = attr
        return self.api_call

    def build_request_url(self, root, endpoint):
        url = '%s%s' % (root, endpoint)
        # encode url params
        return url

    def api_call(self, *args, **kwargs):
        if self._endpoint not in ENDPOINTS:
            raise NotImplementedError('API endpoint for method "%s" is not found.' % self._endpoint)

        meta = ENDPOINTS[self._endpoint]

        params = self.check_params(meta, kwargs)

        if params['url'] != []:
            endpoint = meta['endpoint'] % tuple(params['url'])
        else:
            endpoint = meta['endpoint']

        url = self.build_request_url(API_URL, endpoint)
        response = self.do_request(meta['request_type'], url, params['data'])

        print response

        if meta['model'] is None:
            return response
        else:
            model = meta['model'].from_json(response)
            model.connect_api(self)
            return model

    def check_params(self, meta, kwargs):
        missing_params = []
        url_params = []

        # page, size and anchor are data_params for get requests

        for param in meta['url_params']:
            p = kwargs.get(param)
            if p is None:
                missing_params.append(param)
            else:
                url_params.append(p)
                del kwargs[param]
        if missing_params:
            raise ParameterError('Missing URL parameters: [%s]' % ', '.join(missing_params))

        # url_params shouldnt have default params, I guess
        data_params = kwargs
        if meta.get('default_params', []) != []:
            default_params = dict(meta['default_params'])
            data_params = dict(default_params.items() + kwargs.items())

        missing_params = []
        for param in meta['required_params']:
            p = data_params.get(param)
            if p is None:
                missing_params.append(param)
        if missing_params:
            raise ParameterError('Missing required parameters: [%s]' % ', '.join(missing_params))

        # Check for unsupported params?

        return {'url': url_params, 'data': data_params}

    def do_request(self, request_type, url, data=None):
        request = {
            'post': requests.post,
            'get': requests.get,
            'delete': requests.delete,
            'put': requests.put
        }[request_type]

        if request_type == 'get':
            params = data
            data = None
        else:
            params = None

        headers = HEADERS.copy()
        if self._session_id:
            headers['vine-session-id'] = self._session_id

        r = request(url, params=params, data=data, headers=headers, verify=False)

        print url

        try:
            response = r.json()
            if response['success'] is not True:
                raise VineError(response['code'], response['error'])
            return response['data']
        except:
            logging.error(r.text)
            raise

    def authenticate(self, user):
        self.user = user
        self._session_id = user.key