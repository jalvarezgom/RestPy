from http import HTTPMethod

import pytest

from restpy import RestPy, RestPyURL
from restpy.auth.raw_token import RestPyAuthRawToken
from tests.conftest import FakeResponse

BASE_URL = "https://{region}.api.riotgames.com"
EUROPE_URL = "https://europe.api.riotgames.com"


class RiotAPI(RestPy):
    # [AUTH]
    auth_module = RestPyAuthRawToken(raw_token="test-raw-token", authorization_key="X-Riot-Token", authorization_value_format="{token}")


@pytest.fixture(scope="module")
def riot_api_wURLs():
    api = RiotAPI(base_url=BASE_URL, base_url_params=[{"name": "region", "is_required": True}])
    api.register(name="me", url="/riot/account/v1/accounts/me", request_methods=[HTTPMethod.GET])
    api.register(
        name="summoner_by_name",
        url="/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}",
        request_methods=[HTTPMethod.GET],
        url_params=[{"name": "gameName", "is_required": True}, {"name": "tagLine", "is_required": True}],
    )
    return api


class TestRPYRawTokenEndpoints:
    """Assertions about the registered RestPyURL, obtained through search_url()."""

    def test_endpoint_without_params(self, riot_api_wURLs):
        url = riot_api_wURLs.search_url(name="me")
        assert isinstance(url, RestPyURL)
        assert url.name == "me"
        assert url.url == "/riot/account/v1/accounts/me"
        assert url.request_methods == [HTTPMethod.GET]
        # Only the base URL's "region" placeholder is a field here.
        assert list(url.url_fields) == ["region"]

    def test_endpoint_with_params(self, riot_api_wURLs):
        url = riot_api_wURLs.search_url(name="summoner_by_name")
        assert isinstance(url, RestPyURL)
        assert url.name == "summoner_by_name"
        assert url.url == "/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}"
        assert sorted(url.url_fields) == ["gameName", "region", "tagLine"]


class TestRPYRawTokenRequests:
    """Assertions about the RESTpyResponse returned by the verbs."""

    def test_get_without_params(self, riot_api_wURLs, transport):
        transport.queue(FakeResponse(200, {"puuid": "abc"}))
        response = riot_api_wURLs.get("me", url_params={"region": "europe"})
        assert response.errors is None
        assert response.status_code == 200
        assert response.url == f"{EUROPE_URL}/riot/account/v1/accounts/me"
        assert response.data == {"puuid": "abc"}
        assert transport.last_call.headers["X-Riot-Token"] == "test-raw-token"

    def test_get_with_params(self, riot_api_wURLs, transport):
        transport.queue(FakeResponse(200, {"gameName": "Voltait", "tagLine": "EUW"}))
        response = riot_api_wURLs.get("summoner_by_name", url_params={"region": "europe", "gameName": "Voltait", "tagLine": "EUW"})
        assert response.errors is None
        assert response.status_code == 200
        assert response.url == f"{EUROPE_URL}/riot/account/v1/accounts/by-riot-id/Voltait/EUW"
        assert response.data["gameName"] == "Voltait"
