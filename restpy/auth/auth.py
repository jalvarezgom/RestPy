import logging


class RestPyAuthModule:
    mode = None

    authorization_key = "Authorization"
    authorization_value_format = "Bearer {token}"
    auth_headers = None

    _logger = None
    _token = None
    _cookies = {}

    def __init__(self, **xtra_params):
        for key, value in xtra_params.items():
            setattr(self, key, value)

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def token(self):
        return self._token

    @property
    def cookies(self):
        return self._cookies

    @property
    def logger(self):
        if not self._logger:
            self._logger = logging.getLogger("restpy")
            if not self._logger.hasHandlers():
                self._logger = logging.getLogger()
        return self._logger

    def login(self, refresh=False):
        raise NotImplementedError('You must implement "login" method.')

    def generate_auth_headers(self, **params):
        self.auth_headers = {self.authorization_key: self.authorization_value_format.format(token=self.token)}
        return self.auth_headers
