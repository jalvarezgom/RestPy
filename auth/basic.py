import logging

from auth.auth import RESTpyAuth
from choices.request_method import RequestMethod
from choices.response_type import RequestDataType


class RESTpyAuthBasic(RESTpyAuth):
    mode = 'BASIC'

    send_auth_in_body = False
    auth_url = None
    username = None
    password = None

    get_token_method = 'json'
    get_token_key = 'token'


    @property
    def auth_params(self):
        return {
            'username': self.username,
            'password': self.password
        }

    def login(self, refresh=False):
        if self.send_auth_in_body:
            response = RequestMethod.request(RequestMethod.POST)(
                f'{self.auth_url}',
                cookies=self.cookies,
                json=self.auth_params
            )
        else:
            response = RequestMethod.request(RequestMethod.POST)(
                f'{self.auth_url}',
                cookies=self.cookies,
                params=self.auth_params
            )
        if response.status_code == 200:
            self._token = RequestDataType.get_token(response, self.get_token_method, self.get_token_key)
        return response.status_code == 200


