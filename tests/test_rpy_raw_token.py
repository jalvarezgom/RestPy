import os
from http import HTTPMethod

import pytest

from restpy import RestPy
from restpy.auth.raw_token import RestPyAuthRawToken

RAW_TOKEN = os.environ.get("RIOT_API_KEY")

pytestmark = pytest.mark.skipif(not RAW_TOKEN, reason="RIOT_API_KEY no esta definida en el entorno")


class RiotAPI(RestPy):
    # [AUTH]
    auth_module = RestPyAuthRawToken(raw_token=RAW_TOKEN, authorization_key="X-Riot-Token", authorization_value_format="{token}")
    _auth_headers: dict = None


@pytest.fixture(scope="class")
def riot_api():
    api = RiotAPI(
        base_url="https://{region}.api.riotgames.com",
        base_url_params=[{"name": "region", "is_required": True}],
    )
    return api


@pytest.fixture(scope="class")
def riot_api_wURLs(riot_api):
    riot_api.register(
        name="me",
        url="/riot/account/v1/accounts/me",
        request_methods=[HTTPMethod.GET],
    )
    riot_api.register(
        name="summoner_by_name",
        url="/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}",
        request_methods=[HTTPMethod.GET],
        url_params=[{"name": "gameName", "is_required": True}, {"name": "tagLine", "is_required": True}],
    )
    return riot_api


class TestRPYRawToken:
    def test_get_without_params(self, riot_api_wURLs):
        url = riot_api_wURLs.get("me", url_params={"region": "europe"})
        assert url
        assert url.name == "me"
        assert url.url == "/riot/account/v1/accounts/me"
        assert url.request_methods == [HTTPMethod.GET]
        assert not url.fields_list

    def test_get_with_params(self, riot_api_wURLs):
        url = riot_api_wURLs.get("summoner_by_name", url_params={"region": "europe", "gameName": "Voltait", "tagLine": "EUW"})
        assert url
        assert url.name == "summoner_by_name"
        assert url.url == "/riot/account/v1/accounts/by-riot-id/test/1234"
        assert url.request_methods == [HTTPMethod.GET]
        assert not url.fields_list
