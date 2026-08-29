from http import HTTPMethod

from auth.auth import RestPyAuthModule
from choices.data_type import DataTypeChoice
from choices.request_method import RequestMethodChoice


class RestPyAuthBasic(RestPyAuthModule):
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
        self.auth_url = auth_url
        self.send_auth_in_body = send_auth_in_body
        self.username = username
        self.password = password
        self.get_token_method = get_token_method
        self.get_token_key = get_token_key
        super().__init__(**xtra_params)

    @property
    def basic_auth_credentials(self):
        return {"username": self.username, "password": self.password}

    def login(self, refresh=False):
        if self.send_auth_in_body:
            (params, body) = ({}, self.basic_auth_credentials)
        else:
            (params, body) = (self.basic_auth_credentials, {})
        self.logger.debug(
            f"[{self.name}] Login action - URL: {self.auth_url} using {self.username} in" f" {'Body' if self.send_auth_in_body else 'Params'}"
        )
        response = RequestMethodChoice.request(HTTPMethod.POST)(f"{self.auth_url}", cookies=self.cookies, params=params, json=body)
        self.logger.debug(f"[{self.name}] Login action - Response: {response.status_code}")
        if response.status_code == 200:
            self._token = DataTypeChoice.get_token(response, self.get_token_method, self.get_token_key)
            self.logger.debug(f"[{self.name}] Login action - Token: {self.token}")
        return response.status_code == 200
