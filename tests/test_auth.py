import json

import pytest

from restpy import RestPyAuthBasic, RestPyAuthDisabled, RestPyAuthModule, RestPyAuthOAuth2, RestPyAuthRawToken
from restpy.exceptions import RestPyAuthException
from tests.conftest import FakeResponse

LOGIN_URL = "https://auth.test/login"
TOKEN_URL = "https://auth.test/token"


class TestAuthModule:
    def test_login_must_be_implemented(self):
        with pytest.raises(NotImplementedError):
            RestPyAuthModule().login()

    def test_extra_arguments_become_attributes(self):
        auth = RestPyAuthModule(authorization_key="X-Key", custom="value")
        assert auth.authorization_key == "X-Key"
        assert auth.custom == "value"

    def test_headers_use_the_configured_key_and_format(self):
        auth = RestPyAuthModule(authorization_key="X-Key", authorization_value_format="Token {token}")
        auth._token = "abc"
        assert auth.generate_auth_headers() == {"X-Key": "Token abc"}
        assert auth.auth_headers == {"X-Key": "Token abc"}

    def test_default_header_is_a_bearer_token(self):
        auth = RestPyAuthModule()
        auth._token = "abc"
        assert auth.generate_auth_headers() == {"Authorization": "Bearer abc"}

    def test_name_is_the_class_name(self):
        assert RestPyAuthDisabled().name == "RestPyAuthDisabled"


class TestDisabledAuth:
    def test_login_succeeds_and_sends_no_headers(self):
        auth = RestPyAuthDisabled()
        assert auth.login() is True
        assert auth.generate_auth_headers() == {}


class TestRawTokenAuth:
    def test_token_is_the_raw_token(self):
        auth = RestPyAuthRawToken(raw_token="abc")
        assert auth.token == "abc"
        assert auth.login() is True

    def test_headers_follow_the_configuration(self):
        auth = RestPyAuthRawToken(raw_token="abc", authorization_key="X-Riot-Token", authorization_value_format="{token}")
        assert auth.generate_auth_headers() == {"X-Riot-Token": "abc"}

    @pytest.mark.parametrize("raw_token", [None, ""])
    def test_login_without_a_token_fails(self, raw_token):
        with pytest.raises(ValueError):
            RestPyAuthRawToken(raw_token=raw_token).login()


class TestBasicAuth:
    @staticmethod
    def make_auth(**kwargs):
        return RestPyAuthBasic(auth_url=LOGIN_URL, send_auth_in_body=True, username="u", password="p", **kwargs)

    def test_token_is_read_from_the_json_response(self, transport):
        transport.queue(FakeResponse(200, {"token": "abc"}))
        auth = self.make_auth()
        assert auth.login() is True
        assert auth.token == "abc"
        assert auth.generate_auth_headers() == {"Authorization": "Bearer abc"}

    def test_login_posts_the_credentials_in_the_body(self, transport):
        transport.queue(FakeResponse(200, {"token": "abc"}))
        self.make_auth().login()
        call = transport.last_call
        assert call.url == LOGIN_URL
        assert call.json == {"username": "u", "password": "p"}
        assert call.params == {}
        assert call.timeout == RestPyAuthBasic.REQUEST_TIMEOUT_SECONDS

    def test_custom_token_key(self, transport):
        transport.queue(FakeResponse(200, {"access": "xyz"}))
        auth = self.make_auth(get_token_key="access")
        auth.login()
        assert auth.token == "xyz"

    def test_token_can_be_read_from_the_text_body(self, transport):
        transport.queue(FakeResponse(200, text="plain-token"))
        auth = self.make_auth(get_token_method="text")
        auth.login()
        assert auth.token == "plain-token"

    @pytest.mark.parametrize("status", [400, 401, 500])
    def test_rejected_login_returns_false_and_keeps_no_token(self, transport, status):
        transport.queue(FakeResponse(status))
        auth = self.make_auth()
        assert auth.login() is False
        assert auth.token is None


class TestOAuth2Auth:
    @pytest.fixture
    def token_file(self, tmp_path):
        path = tmp_path / "token.json"
        path.write_text(json.dumps({"access_token": "old", "refresh_token": "keep"}))
        return path

    def make_auth(self, path, **kwargs):
        return RestPyAuthOAuth2(client_id="id", client_secret="secret", oauth_filepath=path, oauth_token_url=TOKEN_URL, **kwargs)

    def test_login_loads_the_token_file(self, token_file):
        auth = self.make_auth(str(token_file))
        assert auth.login() is True
        assert auth.token == {"access_token": "old", "refresh_token": "keep"}

    def test_headers_use_the_access_token(self, token_file):
        auth = self.make_auth(str(token_file))
        auth.login()
        assert auth.generate_auth_headers() == {"Authorization": "Bearer old"}

    def test_refresh_posts_the_stored_refresh_token(self, transport, token_file):
        auth = self.make_auth(str(token_file))
        auth.login()
        transport.queue(FakeResponse(200, {"access_token": "new"}))
        auth.login(refresh=True)
        call = transport.last_call
        assert call.url == TOKEN_URL
        assert call.data == {"refresh_token": "keep", "grant_type": "refresh_token", "client_id": "id", "client_secret": "secret"}
        assert call.timeout == RestPyAuthOAuth2.REQUEST_TIMEOUT_SECONDS

    def test_rejected_refresh_returns_false_and_leaves_the_file_alone(self, transport, token_file):
        auth = self.make_auth(str(token_file))
        auth.login()
        before = token_file.read_text()
        transport.queue(FakeResponse(400))
        assert auth.login(refresh=True) is False
        assert token_file.read_text() == before
        assert auth.token["access_token"] == "old"

    def test_file_path_is_required_to_load(self):
        with pytest.raises(RestPyAuthException):
            self.make_auth(None).login()

    def test_file_path_is_required_to_save(self):
        with pytest.raises(RestPyAuthException):
            self.make_auth(None).dump_oauth_token({"access_token": "x"})
