from http import HTTPMethod

from restpy.auth.auth import RestPyAuthModule
from restpy.choices.data_type import DataTypeChoice
from restpy.choices.request_method import RequestMethodChoice


class RestPyAuthBasic(RestPyAuthModule):
    """Log in by POSTing a username and password, then use the returned token as a bearer token.

    The credentials go in the JSON body (`send_auth_in_body=True`) or in the query string
    (`False`, which can leak them into server logs and proxies).
    """

    mode = "BASIC"

    send_auth_in_body = False
    auth_url = None
    username = None
    password = None

    get_token_method = "json"
    get_token_key = "token"

    def __init__(
        self,
        *,
        auth_url: str,
        send_auth_in_body: bool,
        username: str,
        password: str,
        get_token_method: str = "json",
        get_token_key: str = "token",
        **xtra_params,
    ):
        """
        Args:
            auth_url: Login endpoint.
            send_auth_in_body: Send the credentials in the body instead of the query string.
            username: Login user.
            password: Login password.
            get_token_method: `requests.Response` attribute holding the token; "json" reads a key from the JSON body.
            get_token_key: Key of the token inside the JSON body.
        """
        self.auth_url = auth_url
        self.send_auth_in_body = send_auth_in_body
        if not send_auth_in_body:
            self.logger.warning(f"[{self.name}] Credentials will be sent in the query string: they can end up in server logs, proxies and history")
        self.username = username
        self.password = password
        self.get_token_method = get_token_method
        self.get_token_key = get_token_key
        super().__init__(**xtra_params)

    @property
    def basic_auth_credentials(self):
        """The credentials as the `username`/`password` dict that gets sent."""
        return {"username": self.username, "password": self.password}

    def login(self, refresh=False):
        """POST the credentials to `auth_url`. Return True when the server answers 200."""
        if self.send_auth_in_body:
            (params, body) = ({}, self.basic_auth_credentials)
        else:
            (params, body) = (self.basic_auth_credentials, {})
        self.logger.debug(
            f"[{self.name}] Login action - URL: {self.auth_url} using {self.username} in {'Body' if self.send_auth_in_body else 'Params'}"
        )
        response = RequestMethodChoice.request(HTTPMethod.POST)(
            f"{self.auth_url}", cookies=self.cookies, params=params, json=body, timeout=self.REQUEST_TIMEOUT_SECONDS, verify=self.ssl_verify
        )
        self.logger.debug(f"[{self.name}] Login action - Response: {response.status_code}")
        if response.status_code == 200:
            self._token = DataTypeChoice.get_token(response, self.get_token_method, self.get_token_key)
            self.logger.debug(f"[{self.name}] Login action - Token received")
        return response.status_code == 200
