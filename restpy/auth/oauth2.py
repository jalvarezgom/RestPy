import json
import os
from http import HTTPMethod

from restpy.auth.auth import RestPyAuthModule
from restpy.choices.request_method import RequestMethodChoice
from restpy.exceptions.auth import RestPyAuthException


class RestPyAuthOAuth2(RestPyAuthModule):
    """OAuth2 using a token stored in a JSON file and refreshed with the `refresh_token` grant.

    The file must already hold the token (with `access_token` and `refresh_token`). A refresh
    merges the provider's answer into it and rewrites the file.
    """

    mode = "OAUTH2"

    client_id = None
    client_secret = None
    oauth_filepath = None
    oauth_token_url = None

    def __init__(self, *, client_id: str, client_secret: str, oauth_filepath: str, oauth_token_url: str, **xtra_params):
        """
        Args:
            client_id: OAuth2 client id.
            client_secret: OAuth2 client secret.
            oauth_filepath: JSON file holding the token.
            oauth_token_url: Endpoint that exchanges the refresh token.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.oauth_filepath = oauth_filepath
        self.oauth_token_url = oauth_token_url
        super().__init__(**xtra_params)

    def generate_auth_headers(self, **xtra_params):
        """Build the auth header from the token's `access_token`."""
        self.auth_headers = {self.authorization_key: self.authorization_value_format.format(token=self.token.get("access_token"))}
        return self.auth_headers

    def load_oauth_token(self):
        """Read the token from `oauth_filepath`. Raises `RestPyAuthException` when no path is set."""
        if not self.oauth_filepath:
            raise RestPyAuthException(f"[{self.name}] oauth_filepath is required")
        with open(self.oauth_filepath, "r") as f:
            self._token = json.load(f)
        return self._token

    def dump_oauth_token(self, oauth_token):
        """Write the token to `oauth_filepath` through a temporary file, so a crash cannot truncate it."""
        if not self.oauth_filepath:
            raise RestPyAuthException(f"[{self.name}] oauth_filepath is required")
        # Write-then-rename so a crash cannot leave a truncated token file behind.
        tmp_path = f"{self.oauth_filepath}.tmp"
        with open(tmp_path, "w") as f:
            json.dump(oauth_token, f)
        os.replace(tmp_path, self.oauth_filepath)

    def login(self, refresh=False):
        """Load the token from the file, or with `refresh=True` exchange the refresh token for a new one.

        Returns False when the provider answers anything other than 200.
        """
        if not refresh:
            self.logger.debug(f"[{self.name}] Load OAuth2 JSON")
            self._token = self.load_oauth_token()
        else:
            self.logger.debug(f"[{self.name}] Refresh OAuth2 token")
            refresh_response = RequestMethodChoice.request(HTTPMethod.POST)(
                f"{self.oauth_token_url}", data=self._oauth2_refresh_credentials(), timeout=self.REQUEST_TIMEOUT_SECONDS
            )
            if refresh_response.status_code != 200:
                self.logger.error(f"[{self.name}] Refresh OAuth2 token failed - {refresh_response.status_code}")
                return False
            self._token = {**(self._token or {}), **refresh_response.json()}
            self.dump_oauth_token(self._token)
            self.logger.debug(f"[{self.name}] Refresh OAuth2 token - JSON updated")
        return self._token is not None

    def _oauth2_refresh_credentials(self, **xtra_params):
        """Form data of the `refresh_token` grant request."""
        return {
            "refresh_token": self.token.get("refresh_token"),
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
