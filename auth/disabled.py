from auth.auth import RestPyAuthModule


class RestPyAuthDisabled(RestPyAuthModule):
    mode = "DISABLED"

    def __init__(self, **xtra_params):
        super().__init__(**xtra_params)

    def generate_auth_headers(self, **params):
        self.auth_headers = {}
        return self.auth_headers

    def login(self, refresh=False):
        return True
