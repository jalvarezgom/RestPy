import json

from auth.auth import RestPyAuthModule
from choices.request_method import RequestMethodChoice
from exceptions.auth import RestPyAuthException


class RestPyAuthOAuth2(RestPyAuthModule):
    mode = "OAUTH2"

    client_id = None
    client_secret = None
    oauth_filepath = None
    oauth_token_url = None

    def __init__(self, *, client_id: str, client_secret: str, oauth_filepath: str, oauth_token_url: str, **xtra_params):
        self.client_id = client_id
        self.client_secret = client_secret
        self.oauth_filepath = oauth_filepath
        self.oauth_token_url = oauth_token_url
        super().__init__(**xtra_params)

    def generate_auth_headers(self, **xtra_params):
        self.auth_headers = {self.authorization_key: self.authorization_value_format.format(token=self.token.get("access_token"))}
        return self.auth_headers

    def load_oauth_token(self):
        if not self.oauth_filepath:
            raise RestPyAuthException(f"[{self.name}] oauth_filepath is required")
        with open(self.oauth_filepath, "r") as f:
            self._token = json.load(f)
        return self._token

    def dump_oauth_token(self, oauth_token):
        if not self.oauth_filepath:
            raise RestPyAuthException(f"[{self.name}] oauth_filepath is required")
        with open(self.oauth_filepath, "w") as f:
            json.dump(oauth_token, f)

    def login(self, refresh=False):
        if not refresh:
            self.logger.debug(f"[{self.name}] Load OAuth2 JSON")
            self._token = self.load_oauth_token()
        else:
            self.logger.debug(f"[{self.name}] Refresh OAuth2 token")
            refresh_response = RequestMethodChoice.request(RequestMethodChoice.POST)(
                f"{self.oauth_token_url}", data=self._oauth2_refresh_credentials()
            )
            if refresh_response.status_code != 200:
                self.logger.error(f"[{self.name}] Refresh OAuth2 token failed - {refresh_response.status_code}")
                return False
            self._token = refresh_response.json()
            self.logger.debug(f"[{self.name}] Refresh OAuth2 token - Value: {self.token}")
            self.dump_oauth_token(self._token)
            self.logger.debug(f"[{self.name}] Refresh OAuth2 token - JSON updated")
        self.logger.debug(f"[{self.name}] OAuth token: {self.token}")
        return self._token is not None

    def _oauth2_refresh_credentials(self, **xtra_params):
        return {
            "refresh_token": self.token.get("refresh_token"),
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
