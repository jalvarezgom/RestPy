from restpy.auth.auth import RestPyAuthModule


class RestPyAuthDisabled(RestPyAuthModule):
    """No authentication: no header is added and `login()` always succeeds."""

    mode = "DISABLED"

    def __init__(self, **xtra_params):
        super().__init__(**xtra_params)

    def generate_auth_headers(self, **params):
        self.auth_headers = {}
        return self.auth_headers

    def login(self, refresh=False):
        return True
