from auth.auth import RestPyAuthModule


class RestPyAuthRawToken(RestPyAuthModule):
    mode = "RAW_TOKEN"

    raw_token = None

    def __init__(self, *, raw_token: str, **xtra_params):
        self.raw_token = raw_token
        super().__init__(**xtra_params)

    @property
    def token(self):
        return self.raw_token

    def login(self, refresh=False):
        if not self.raw_token:
            raise ValueError('You must set "raw_token" property before login.')
        return True
