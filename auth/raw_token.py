import logging

from auth.auth import RESTpyAuth


class RESTpyAuthRawToken(RESTpyAuth):
    mode = 'RAW_TOKEN'

    raw_token = None

    @property
    def token(self):
        return self.raw_token

    def login(self, refresh=False):
        if not self.raw_token:
            raise ValueError('You must set "raw_token" property before login.')
        return True
