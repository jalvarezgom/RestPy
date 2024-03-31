import logging


class RESTpyAuth:
    mode = None

    _authorization_key = 'Authorization'
    _authorization_header = 'Bearer {token}'

    _logger = None
    _token = None
    _cookies = {}

    def __init__(self, **params):
        for key, value in params.items():
            setattr(self, key, value)

    @property
    def token(self):
        return self._token

    @property
    def cookies(self):
        return self._cookies

    @property
    def logger(self):
        if not self._logger:
            self._logger = logging.getLogger()
        return self._logger

    def login(self, refresh=False):
        raise NotImplementedError('You must implement "login_method" method.')

    def generate_auth_headers(self, **params):
        return {self._authorization_key: self._authorization_header.format(token=self.token)}

