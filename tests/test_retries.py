from http import HTTPMethod, HTTPStatus

import pytest
import requests

import restpy.classes.module as module_under_test
from restpy import RestPy, RestPyAuthDisabled, RestPyAuthModule
from restpy.exceptions import RESTpyTimeOutException, RestPyConnectionException, RestPyIsSuccessResponse
from tests.conftest import FakeResponse


@pytest.fixture
def sleeps(monkeypatch):
    """Records the delays instead of waiting for them."""
    calls = []
    monkeypatch.setattr(module_under_test.time, "sleep", calls.append)
    return calls


def make_api(auth=None):
    api = RestPy(base_url="https://retries.test", auth_action=auth or RestPyAuthDisabled())
    api.register(name="ping", url="/ping", request_methods=[HTTPMethod.GET, HTTPMethod.POST])
    return api


class RefreshRaisesAuth(RestPyAuthModule):
    """Logs in fine, but the network drops while the token is refreshed."""

    def login(self, refresh=False):
        if refresh:
            raise requests.ConnectionError("down")
        self._token = "stale"
        return True


class TestStatusRetries:
    def test_retries_a_gateway_timeout_and_waits(self, transport, sleeps):
        transport.queue(FakeResponse(504), FakeResponse(200, {"ok": True}))
        api = make_api()
        response = api.get("ping")
        assert response.status_code == 200
        assert response.errors is None
        assert len(transport.calls) == 2
        assert sleeps == [api.RETRIES_TIMEOUT_SECONDS]

    def test_stops_after_retries_url_attempts(self, transport, sleeps):
        transport.queue(FakeResponse(504), FakeResponse(504), FakeResponse(504), FakeResponse(200, {}))
        api = make_api()
        response = api.get("ping")
        assert len(transport.calls) == api.RETRIES_URL == 3
        assert response.status_code == 504
        assert isinstance(response.errors[0], RestPyIsSuccessResponse)

    def test_retries_url_is_configurable(self, transport, sleeps):
        api = make_api()
        api.RETRIES_URL = 2
        transport.queue(FakeResponse(504), FakeResponse(504), FakeResponse(200, {}))
        api.get("ping")
        assert len(transport.calls) == 2

    def test_retry_without_delay(self, transport, sleeps):
        api = make_api()
        api.RETRIES_TIMEOUT_STATUS_CODES = []
        api.RETRIES_STATUS_CODES = [HTTPStatus.INTERNAL_SERVER_ERROR]
        transport.queue(FakeResponse(500), FakeResponse(200, {}))
        assert api.get("ping").status_code == 200
        assert len(transport.calls) == 2
        assert sleeps == []

    def test_other_statuses_are_not_retried(self, transport, sleeps):
        transport.queue(FakeResponse(404), FakeResponse(200, {}))
        response = make_api().get("ping")
        assert response.status_code == 404
        assert len(transport.calls) == 1
        assert sleeps == []


class TestTimeoutRetries:
    def test_timeout_is_retried_after_a_delay(self, transport, sleeps):
        transport.queue(requests.Timeout("slow"), FakeResponse(200, {"ok": True}))
        api = make_api()
        response = api.get("ping")
        assert response.status_code == 200
        assert len(transport.calls) == 2
        assert sleeps == [api.RETRIES_TIMEOUT_SECONDS]

    def test_exhausted_timeouts_return_a_timeout_error(self, transport, sleeps):
        transport.queue(requests.Timeout("a"), requests.Timeout("b"), requests.Timeout("c"))
        api = make_api()
        response = api.get("ping")
        assert isinstance(response.errors[0], RESTpyTimeOutException)
        assert response.status_code is None
        assert len(transport.calls) == api.RETRIES_URL
        assert len(sleeps) == api.RETRIES_URL - 1

    def test_every_attempt_carries_the_timeout(self, transport, sleeps):
        api = make_api()
        api.REQUEST_TIMEOUT_SECONDS = 7
        transport.queue(FakeResponse(504), FakeResponse(200, {}))
        api.get("ping")
        assert [call.timeout for call in transport.calls] == [7, 7]

    def test_ssl_verify_defaults_to_true_on_every_attempt(self, transport, sleeps):
        api = make_api()
        transport.queue(FakeResponse(504), FakeResponse(200, {}))
        api.get("ping")
        assert [call.verify for call in transport.calls] == [True, True]

    def test_ssl_verify_false_is_sent_to_requests(self, transport):
        api = make_api()
        api.ssl_verify = False
        api.get("ping")
        assert all(call.verify is False for call in transport.calls)

    def test_ssl_verify_can_be_set_in_the_constructor(self):
        assert type(make_api())(ssl_verify="/ca.pem").ssl_verify == "/ca.pem"


class TestRefreshFailures:
    def test_network_error_while_refreshing_is_returned(self, transport):
        transport.queue(FakeResponse(401))
        response = make_api(RefreshRaisesAuth()).get("ping")
        assert isinstance(response.errors[0], RestPyConnectionException)
        assert response.status_code == 401
        assert len(transport.calls) == 1
