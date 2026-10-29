import datetime
import json
import logging
from http import HTTPMethod

import pytest
import requests

from restpy import RestPy, RestPyAuthBasic, RestPyAuthDisabled, RestPyAuthModule, RestPyAuthOAuth2
from restpy.exceptions import RESTpyTimeOutException, RestPyConnectionException, RestPyLoginException, RestPyURLParamsException
from restpy.validators import DatetimeObjectValidator, DateYearMonthDayValidator
from tests.conftest import FakeResponse


class FailingAuth(RestPyAuthModule):
    def login(self, refresh=False):
        return False


class RejectedRefreshAuth(RestPyAuthModule):
    """Logs in fine, but the refresh that follows a 401 fails."""

    def login(self, refresh=False):
        if refresh:
            return False
        self._token = "stale"
        return True


def make_api(auth):
    api = RestPy(base_url="https://hardening.test", auth_action=auth)
    api.register(name="ping", url="/ping", request_methods=[HTTPMethod.GET, HTTPMethod.POST])
    return api


class TestFailedLogin:
    """RP-025: a failed login must not send the request with `Bearer None`."""

    def test_failed_login_returns_error_without_sending(self, transport):
        response = make_api(FailingAuth()).get("ping")
        assert isinstance(response.errors[0], RestPyLoginException)
        assert transport.calls == []

    def test_rejected_refresh_returns_error(self, transport):
        transport.queue(FakeResponse(401))
        response = make_api(RejectedRefreshAuth()).get("ping")
        assert isinstance(response.errors[0], RestPyLoginException)
        assert response.status_code == 401


class TestNetworkErrors:
    """RP-035: network failures come back in `errors` instead of being raised."""

    def test_connection_error_is_returned(self, transport):
        transport.queue(requests.ConnectionError("refused"))
        response = make_api(RestPyAuthDisabled()).get("ping")
        assert isinstance(response.errors[0], RestPyConnectionException)
        assert response.status_code is None

    def test_connection_error_during_login_is_returned(self, transport):
        transport.queue(requests.ConnectionError("dns"))
        auth = RestPyAuthBasic(auth_url="https://hardening.test/login", send_auth_in_body=True, username="u", password="p")
        response = make_api(auth).get("ping")
        assert isinstance(response.errors[0], RestPyConnectionException)

    def test_timeout_during_login_is_a_timeout_error(self, transport):
        transport.queue(requests.Timeout("slow"))
        auth = RestPyAuthBasic(auth_url="https://hardening.test/login", send_auth_in_body=True, username="u", password="p")
        response = make_api(auth).get("ping")
        assert isinstance(response.errors[0], RESTpyTimeOutException)


class TestOAuth2Refresh:
    """RP-026: a refresh response without `refresh_token` must not drop the stored one."""

    @pytest.fixture
    def token_file(self, tmp_path):
        path = tmp_path / "token.json"
        path.write_text(json.dumps({"access_token": "old", "refresh_token": "keep-me"}))
        return path

    def test_refresh_token_survives_refresh(self, transport, token_file):
        auth = RestPyAuthOAuth2(
            client_id="id", client_secret="secret", oauth_filepath=str(token_file), oauth_token_url="https://hardening.test/token"
        )
        auth.login()
        transport.queue(FakeResponse(200, {"access_token": "new"}))
        assert auth.login(refresh=True)
        stored = json.loads(token_file.read_text())
        assert stored == {"access_token": "new", "refresh_token": "keep-me"}
        assert not list(token_file.parent.glob("*.tmp"))

    def test_new_refresh_token_replaces_old(self, transport, token_file):
        auth = RestPyAuthOAuth2(
            client_id="id", client_secret="secret", oauth_filepath=str(token_file), oauth_token_url="https://hardening.test/token"
        )
        auth.login()
        transport.queue(FakeResponse(200, {"access_token": "new", "refresh_token": "rotated"}))
        auth.login(refresh=True)
        assert json.loads(token_file.read_text())["refresh_token"] == "rotated"


class TestDatetimeValidator:
    """RP-028: `str` and `datetime` inputs are handled in the right direction."""

    def test_string_validator_keeps_str(self):
        assert DateYearMonthDayValidator.validate("d", "2024-01-31") == ("2024-01-31", None)

    def test_string_validator_formats_datetime(self):
        assert DateYearMonthDayValidator.validate("d", datetime.datetime(2024, 1, 31)) == ("2024-01-31", None)

    def test_string_validator_rejects_bad_str(self):
        value, error = DateYearMonthDayValidator.validate("d", "31/01/2024")
        assert value is None and error is not None

    def test_object_validator_parses_str(self):
        assert DatetimeObjectValidator.validate("d", "2024-01-31T10:00:00") == (datetime.datetime(2024, 1, 31, 10), None)

    def test_object_validator_keeps_datetime(self):
        now = datetime.datetime(2024, 1, 31, 10)
        assert DatetimeObjectValidator.validate("d", now) == (now, None)

    def test_non_str_is_rejected(self):
        _, error = DateYearMonthDayValidator.validate("d", 20240131)
        assert error is not None


class TestNoSecretsInLogs:
    """RP-032: tokens and bodies never reach the logs."""

    def test_basic_oauth_and_body_are_not_logged(self, transport, caplog, tmp_path):
        caplog.set_level(logging.DEBUG)
        transport.queue(FakeResponse(200, {"token": "SECRET-TOKEN"}), FakeResponse(200, {"ok": True}))
        auth = RestPyAuthBasic(auth_url="https://hardening.test/login", send_auth_in_body=True, username="u", password="p")
        make_api(auth).post("ping", data_params={"password": "SECRET-BODY"})

        path = tmp_path / "token.json"
        path.write_text(json.dumps({"access_token": "SECRET-ACCESS", "refresh_token": "SECRET-REFRESH"}))
        oauth = RestPyAuthOAuth2(client_id="id", client_secret="s", oauth_filepath=str(path), oauth_token_url="https://hardening.test/token")
        oauth.login()
        transport.queue(FakeResponse(200, {"access_token": "SECRET-NEW"}))
        oauth.login(refresh=True)

        assert "SECRET" not in caplog.text


class CountingAuth(RestPyAuthModule):
    def __init__(self):
        super().__init__()
        self.logins = []

    def login(self, refresh=False):
        self.logins.append(refresh)
        self._token = "tok"
        return True


class TestForbiddenDoesNotRefresh:
    """RP-027: a 403 is returned as-is; only a 401 refreshes the login."""

    def test_default_codes_only_contain_401(self):
        assert RestPy.REFRESH_LOGIN_STATUS_CODES == [401]

    def test_403_is_not_refreshed(self, transport):
        transport.queue(FakeResponse(403))
        auth = CountingAuth()
        response = make_api(auth).get("ping")
        assert response.status_code == 403
        assert auth.logins == [False]
        assert len(transport.calls) == 1

    def test_401_is_refreshed_once(self, transport):
        transport.queue(FakeResponse(401), FakeResponse(200, {}))
        auth = CountingAuth()
        make_api(auth).get("ping")
        assert auth.logins == [False, True]


class TestURLParams:
    """RP-030: falsy values are substituted; unresolved or undeclared params are errors."""

    @pytest.fixture
    def api(self):
        api = RestPy(base_url="https://hardening.test", auth_action=RestPyAuthDisabled())
        api.register(name="item", url="/items/{id}", request_methods=[HTTPMethod.GET], url_params=[{"name": "id", "is_required": False}])
        return api

    @pytest.mark.parametrize("value", [0, ""])
    def test_falsy_value_is_substituted(self, api, transport, value):
        api.get("item", url_params={"id": value})
        assert transport.last_call.url == f"https://hardening.test/items/{value}"

    def test_unresolved_placeholder_is_an_error(self, api, transport):
        response = api.get("item")
        assert isinstance(response.errors[0], RestPyURLParamsException)
        assert transport.calls == []

    def test_undeclared_param_is_an_error(self, api, transport):
        response = api.get("item", url_params={"id": 1, "other": 2})
        assert isinstance(response.errors[0], RestPyURLParamsException)
        assert transport.calls == []
