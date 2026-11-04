from http import HTTPMethod, HTTPStatus

import pytest

from restpy import RestPy, RestPyAuthDisabled
from tests.conftest import FakeResponse

BASE_URL = "https://verbs.test"
ALL_VERBS = [HTTPMethod.GET, HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.PATCH, HTTPMethod.DELETE]


class EchoAPI(RestPy):
    auth_module = RestPyAuthDisabled()

    def register_urls(self):
        self.register(name="echo", url="/echo", request_methods=ALL_VERBS)


class BareAPI(RestPy):
    """No endpoints: safe to instantiate more than once (see RP-007)."""

    auth_module = RestPyAuthDisabled()


@pytest.fixture(scope="module")
def echo_api():
    return EchoAPI(base_url=BASE_URL)


class TestVerbs:
    """RP-001: every verb reaches the transport, not just `get`."""

    @pytest.mark.parametrize("verb", ["get", "post", "put", "patch", "delete"])
    def test_verb_emits_request(self, echo_api, transport, verb):
        transport.queue(FakeResponse(200, {"ok": True}))
        response = getattr(echo_api, verb)("echo")
        assert response.errors is None
        assert response.status_code == 200
        assert transport.last_call.method == HTTPMethod[verb.upper()]
        assert transport.last_call.url == f"{BASE_URL}/echo"

    def test_verb_accepts_url_str(self, echo_api, transport):
        transport.queue(FakeResponse(200, {"ok": True}))
        response = echo_api.post(url_str="/echo")
        assert response.status_code == 200


class TestSearchURL:
    """RP-003: lookup by path."""

    def test_search_by_url_returns_endpoint(self, echo_api):
        assert echo_api.search_url(url_str="/echo") is echo_api.search_url(name="echo")

    def test_search_by_unknown_url_returns_none(self, echo_api):
        assert echo_api.search_url(url_str="/not-registered") is None


class TestClientIsolation:
    """RP-006: configuration is per instance, not shared through the class."""

    def test_valid_status_is_not_shared(self):
        one, other = BareAPI(base_url=BASE_URL), BareAPI(base_url=BASE_URL)
        one.add_valid_status(HTTPStatus.ACCEPTED)
        assert HTTPStatus.ACCEPTED in one._VALID_STATUS
        assert HTTPStatus.ACCEPTED not in other._VALID_STATUS
        assert HTTPStatus.ACCEPTED not in BareAPI._VALID_STATUS

    def test_headers_are_not_shared(self):
        one, other = BareAPI(base_url=BASE_URL, headers={"X-One": "1"}), BareAPI(base_url=BASE_URL)
        assert one.headers == {"X-One": "1"}
        assert other.headers == {}
