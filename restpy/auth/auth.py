import logging


class RestPyAuthModule:
    """Base class of the authentication strategies.

    Subclasses implement `login()`, which obtains the token, and may override
    `generate_auth_headers()`. Keyword arguments given to the constructor are set as attributes,
    so class-level settings can be overridden per instance.

    Attributes:
        authorization_key: Name of the auth header.
        authorization_value_format: Header value template; `{token}` is replaced with the token.
        REQUEST_TIMEOUT_SECONDS: Timeout of the module's own network calls.
    """

    mode = None

    REQUEST_TIMEOUT_SECONDS = 30

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
        """Class name, used in logs and messages."""
        return self.__class__.__name__

    @property
    def token(self):
        """The current token, or None before the first login."""
        return self._token

    @property
    def cookies(self):
        """Cookies sent with every request. Nothing in the library fills them: it is an empty dict unless you set `_cookies`."""
        return self._cookies

    @property
    def logger(self):
        """The `restpy` logger, or the root logger when `restpy` has no handlers configured."""
        if not self._logger:
            self._logger = logging.getLogger("restpy")
            if not self._logger.hasHandlers():
                self._logger = logging.getLogger()
        return self._logger

    def login(self, refresh=False):
        """Obtain the token. Return True on success, False on failure.

        Args:
            refresh: True when called after the server rejected the current token.
        """
        raise NotImplementedError('You must implement "login" method.')

    def generate_auth_headers(self, **params):
        """Build `auth_headers` from the token and the header key/value template, and return them."""
        self.auth_headers = {self.authorization_key: self.authorization_value_format.format(token=self.token)}
        return self.auth_headers
