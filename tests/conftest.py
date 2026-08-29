import json
from types import SimpleNamespace
from urllib.parse import urlencode

import pytest

from restpy import RestPy
from restpy.auth.raw_token import RestPyAuthRawToken
from restpy.choices.request_method import RequestMethodChoice


class FakeResponse:
    """Minimal stand-in for `requests.Response` covering what RestPy reads."""

    def __init__(self, status_code=200, json_data=None, text=None):
        self.status_code = status_code
        self._json_data = json_data
        if text is not None:
            self.text = text
        elif json_data is not None:
            self.text = json.dumps(json_data)
        else:
            self.text = ""
        self.url = ""
        self.request = SimpleNamespace(url="")

    def json(self):
        if self._json_data is None:
            raise ValueError("No JSON object could be decoded")
        return self._json_data


class FakeTransport:
    """Replacement for `RequestMethodChoice.request`: records calls, replays queued responses."""

    def __init__(self):
        self.calls = []
        self._queue = []
        self.default_response = FakeResponse(200, {})

    def queue(self, *responses):
        self._queue.extend(responses)

    @property
    def last_call(self):
        return self.calls[-1] if self.calls else None

    def request(self, method, session=None):
        # `session` is accepted (and ignored) so the fake matches RequestMethodChoice.request.
        def _send(url, params=None, data=None, headers=None, cookies=None, timeout=None):
            self.calls.append(
                SimpleNamespace(
                    method=method, url=url, params=dict(params or {}), data=data, headers=dict(headers or {}), cookies=cookies, timeout=timeout
                )
            )
            response = self._queue.pop(0) if self._queue else self.default_response
            response.url = f"{url}?{urlencode(params)}" if params else url
            response.request = SimpleNamespace(url=response.url)
            return response

        return _send


@pytest.fixture
def transport(monkeypatch):
    """Cuts the suite off from the network by swapping out the HTTP verb resolver."""
    fake = FakeTransport()
    monkeypatch.setattr(RequestMethodChoice, "request", fake.request)
    return fake


@pytest.fixture
def api():
    return RestPy(
        base_url="https://example.test",
        auth_action=RestPyAuthRawToken(raw_token="test-token", authorization_key="X-Test-Token", authorization_value_format="{token}"),
    )
