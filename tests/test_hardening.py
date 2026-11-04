import datetime
import json
import logging
from http import HTTPMethod

import pytest
import requests

from restpy import DataTypeChoice, RESTpyField, RestPy, RestPyAuthBasic, RestPyAuthDisabled, RestPyAuthModule, RestPyAuthOAuth2
from restpy.exceptions import RESTpyTimeOutException, RestPyConnectionException, RestPyLoginException, RestPyURLParamsException, RestPyValidatorException
from restpy.classes.url import RestPyFieldWhereData
from restpy.validators.required_field import RequiredFieldValidator
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


class TestSameNameFields:
    """RP-031: a field name reused in URL, query and body keeps one definition per location."""

    @pytest.fixture
    def api(self):
        api = RestPy(base_url="https://hardening.test", auth_action=RestPyAuthDisabled())
        api.register(
            name="item",
            url="/items/{id}",
            request_methods=[HTTPMethod.POST],
            url_params=[{"name": "id", "is_required": True}],
            data_params=[{"name": "id", "is_required": True}],
        )
        return api

    def test_both_fields_are_kept(self, api):
        rp_url = api.search_url(name="item")
        assert len(rp_url.fields_list) == 2
        assert set(rp_url.url_fields) == {"id"} and set(rp_url.data_fields) == {"id"}
        assert rp_url.get_field("id", RestPyFieldWhereData.URL_PARAMS).where_data == RestPyFieldWhereData.URL_PARAMS
        assert rp_url.get_field("id", RestPyFieldWhereData.BODY).where_data == RestPyFieldWhereData.BODY

    def test_missing_url_field_is_validated(self, api, transport):
        response = api.post("item", data_params={"id": 1})
        assert isinstance(response.errors[0], RestPyValidatorException)
        assert transport.calls == []

    def test_missing_body_field_is_validated(self, api, transport):
        response = api.post("item", url_params={"id": 1})
        assert isinstance(response.errors[0], RestPyValidatorException)
        assert transport.calls == []

    def test_both_present_sends_request(self, api, transport):
        api.post("item", url_params={"id": 1}, data_params={"id": 2})
        assert transport.last_call.url == "https://hardening.test/items/1"


class TestBasicAuthCredentialsPlacement:
    """RP-033: the user must choose explicitly; the query string option warns."""

    LOGIN = "https://hardening.test/login"

    def test_choice_is_required(self):
        with pytest.raises(TypeError):
            RestPyAuthBasic(auth_url=self.LOGIN, username="u", password="p")

    def test_body_sends_no_query_params(self, transport):
        transport.queue(FakeResponse(200, {"token": "t"}))
        auth = RestPyAuthBasic(auth_url=self.LOGIN, username="u", password="p", send_auth_in_body=True)
        assert auth.login()
        assert transport.last_call.params == {}

    def test_query_string_warns(self, transport, caplog):
        caplog.set_level(logging.WARNING)
        transport.queue(FakeResponse(200, {"token": "t"}))
        auth = RestPyAuthBasic(auth_url=self.LOGIN, username="u", password="p", send_auth_in_body=False)
        assert "query string" in caplog.text
        assert auth.login()
        assert transport.last_call.params == {"username": "u", "password": "p"}


class TestRequiredFalsyValues:
    """RP-034: only an absent key, `None` and (by default) `""` count as missing."""

    @staticmethod
    def make_field(**kwargs):
        return RESTpyField(where_data=RestPyFieldWhereData.BODY, name="f", is_required=True, **kwargs)

    @pytest.mark.parametrize("value", [0, 0.0, False, [], {}])
    def test_falsy_values_pass(self, value):
        _, error = RequiredFieldValidator.validate(self.make_field(), {"f": value})
        assert error is None

    @pytest.mark.parametrize("data", [{}, {"f": None}, {"f": ""}])
    def test_missing_values_fail(self, data):
        _, error = RequiredFieldValidator.validate(self.make_field(), data)
        assert error is not None

    def test_empty_string_passes_with_allow_empty(self):
        _, error = RequiredFieldValidator.validate(self.make_field(allow_empty=True), {"f": ""})
        assert error is None

    def test_allow_empty_still_rejects_none(self):
        _, error = RequiredFieldValidator.validate(self.make_field(allow_empty=True), {"f": None})
        assert error is not None

    def test_allow_empty_must_be_a_bool(self):
        with pytest.raises(ValueError):
            self.make_field(allow_empty="yes")

    def test_zero_is_sent_end_to_end(self, transport):
        api = RestPy(base_url="https://hardening.test", auth_action=RestPyAuthDisabled())
        api.register(name="page", url="/page", request_methods=[HTTPMethod.GET], query_params=[{"name": "offset", "is_required": True}])
        api.get("page", query_params={"offset": 0})
        assert transport.last_call.params == {"offset": 0}


class TestResponseDataTypes:
    """RP-036: TEXT returns the body, bad XML falls back to the text, DICT is not a response type."""

    @staticmethod
    def make_api(data_type):
        api = RestPy(base_url="https://hardening.test", auth_action=RestPyAuthDisabled())
        api.register(name="doc", url="/doc", request_methods=[HTTPMethod.GET], response_data_type=data_type)
        return api

    def test_text_returns_the_body(self, transport):
        transport.queue(FakeResponse(200, text="plain body"))
        response = self.make_api(DataTypeChoice.TEXT).get("doc")
        assert response.data == "plain body"
        assert response.errors is None

    def test_valid_xml_is_parsed(self, transport):
        transport.queue(FakeResponse(200, text="<a><b>1</b></a>"))
        assert self.make_api(DataTypeChoice.XML).get("doc").data == {"a": {"b": "1"}}

    def test_invalid_xml_falls_back_to_text(self, transport):
        transport.queue(FakeResponse(200, text="<html><body>oops"))
        response = self.make_api(DataTypeChoice.XML).get("doc")
        assert response.data == "<html><body>oops"
        assert response.status_code == 200

    def test_dict_is_rejected_as_response_type(self):
        with pytest.raises(ValueError, match="DICT"):
            self.make_api(DataTypeChoice.DICT)

    def test_dict_is_still_valid_as_request_type(self):
        api = RestPy(base_url="https://hardening.test", auth_action=RestPyAuthDisabled())
        api.register(name="doc", url="/doc", request_methods=[HTTPMethod.POST], request_data_type=DataTypeChoice.DICT)


class TestLoginRefreshDoesNotConsumeAnAttempt:
    """RP-037: the request re-sent after a 401 refresh does not count against RETRIES_URL."""

    def test_refresh_is_retried_with_a_single_attempt(self, transport):
        transport.queue(FakeResponse(401), FakeResponse(200, {"ok": True}))
        auth = CountingAuth()
        api = make_api(auth)
        api.RETRIES_URL = 1
        response = api.get("ping")
        assert response.status_code == 200
        assert auth.logins == [False, True]
        assert len(transport.calls) == 2

    def test_refresh_happens_only_once(self, transport):
        transport.queue(FakeResponse(401), FakeResponse(401), FakeResponse(401))
        auth = CountingAuth()
        api = make_api(auth)
        api.RETRIES_URL = 1
        response = api.get("ping")
        assert response.status_code == 401
        assert auth.logins == [False, True]
        assert len(transport.calls) == 2
