import json
import logging

from auth.auth import RESTpyAuth
from choices.request_method import RequestMethod
from choices.response_type import RequestDataType
from exceptions.auth import RESTpyAuthException


class RESTpyAuthOAuth2(RESTpyAuth):
    mode = 'OAUTH2'

    client_id = None
    client_secret = None
    oauth_filepath = None
    oauth_token_url = None

    def login(self, refresh=False):
        if not refresh:
            self._token = self.load_oauth_token()
        else:
            refresh_response = RequestMethod.request(RequestMethod.POST)(
                f'{self.oauth_token_url}',
                data=self.__params_refresh_token()
            )
            self._token = refresh_response.json()
            self.dump_oauth_token(self._token)
        return True

    def __params_refresh_token(self):
        return {
            'refresh_token': self.token.get('refresh_token'),
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }

    def load_oauth_token(self):
        if not self.oauth_filepath:
            raise RESTpyAuthException('oauth_filepath is required')
        with open(self.oauth_filepath, 'r') as f:
            self._token = json.load(f)
        return self._token

    def dump_oauth_token(self, oauth_token):
        if not self.oauth_filepath:
            raise RESTpyAuthException('oauth_filepath is required')
        with open(self.oauth_filepath, 'w') as f:
            json.dump(oauth_token, f)

    def generate_auth_headers(self, **params):
        return {self._authorization_key: self._authorization_header.format(token=self.token.get('access_token'))}
