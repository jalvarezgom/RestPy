from http import HTTPMethod

import pytest

from restpy import RestPy, RestPyAuthDisabled, RestPyURL
from restpy.exceptions.request import RestPyRequestMethodException, RestPyURLNotFoundException
from restpy.exceptions.status_codes import RestPyIsSuccessResponse
from restpy.exceptions.validators import RestPyValidatorException
from restpy.validators import NumberValidator, StrValidator
from tests.conftest import FakeResponse

BASE_URL = "https://pokeapi.test/api/v2"


class MockedAPI(RestPy):
    # [AUTH] Public API: no credentials needed
    auth_module = RestPyAuthDisabled()

    def register_urls(self):
        self.register(
            name="mock_pokemon_by_name",
            url="/pokemon/{name}",
            request_methods=[HTTPMethod.GET],
            url_params=[{"name": "name", "is_required": True, "validator": StrValidator()}],
        )
        self.register(
            name="mock_pokemon_list",
            url="/pokemon",
            request_methods=[HTTPMethod.GET],
            query_params=[
                {"name": "limit", "is_required": True, "validator": NumberValidator()},
                {"name": "offset", "validator": NumberValidator()},
            ],
        )
        self.register(
            name="mock_ability_by_id",
            url="/ability/{id}",
            request_methods=[HTTPMethod.GET],
            url_params=[{"name": "id", "is_required": True, "validator": StrValidator()}],
        )


@pytest.fixture(scope="module")
def mock_api():
    return MockedAPI(base_url=BASE_URL)


class TestRPYMocked:
    def test_registered_urls(self, mock_api):
        url = mock_api.search_url(name="mock_pokemon_by_name")
        assert isinstance(url, RestPyURL)
        assert url.url == "/pokemon/{name}"
        assert list(url.url_fields) == ["name"]
        assert sorted(mock_api.search_url(name="mock_pokemon_list").query_fields) == ["limit", "offset"]

    def test_get_with_url_params(self, mock_api, transport):
        transport.queue(FakeResponse(200, {"name": "ditto", "id": 132}))
        response = mock_api.get("mock_pokemon_by_name", url_params={"name": "ditto"})
        assert response.errors is None
        assert response.status_code == 200
        assert response.url == f"{BASE_URL}/pokemon/ditto"
        assert response.data["name"] == "ditto"
        assert response.data["id"] == 132

    def test_get_with_query_params(self, mock_api, transport):
        transport.queue(FakeResponse(200, {"count": 1302, "results": [{"name": f"p{i}"} for i in range(5)]}))
        response = mock_api.get("mock_pokemon_list", query_params={"limit": 5, "offset": 20})
        assert response.errors is None
        assert response.status_code == 200
        assert len(response.data["results"]) == 5
        assert transport.last_call.params == {"limit": 5, "offset": 20}

    def test_get_casts_url_param_with_validator(self, mock_api, transport):
        # StrValidator turns the number into a str so the URL can be formatted
        transport.queue(FakeResponse(200, {"name": "stench"}))
        response = mock_api.get("mock_ability_by_id", url_params={"id": 1})
        assert response.errors is None
        assert response.url == f"{BASE_URL}/ability/1"
        assert response.data["name"] == "stench"

    def test_get_missing_required_url_param(self, mock_api, transport):
        response = mock_api.get("mock_pokemon_by_name", url_params={})
        assert response.status_code is None
        assert len(response.errors) == 1
        assert isinstance(response.errors[0], RestPyValidatorException)
        assert transport.calls == []

    def test_get_invalid_query_param_type(self, mock_api, transport):
        response = mock_api.get("mock_pokemon_list", query_params={"limit": 5, "offset": "veinte"})
        assert response.status_code is None
        assert len(response.errors) == 1
        assert isinstance(response.errors[0], RestPyValidatorException)
        assert transport.calls == []

    def test_get_not_found_status(self, mock_api, transport):
        transport.queue(FakeResponse(404, text="Not Found"))
        response = mock_api.get("mock_pokemon_by_name", url_params={"name": "does-not-exist"})
        assert response.status_code == 404
        assert response.url == f"{BASE_URL}/pokemon/does-not-exist"
        assert len(response.errors) == 1
        assert isinstance(response.errors[0], RestPyIsSuccessResponse)

    def test_request_method_not_allowed(self, mock_api, transport):
        response = mock_api.post("mock_pokemon_by_name", url_params={"name": "ditto"})
        assert response.status_code is None
        assert len(response.errors) == 1
        assert isinstance(response.errors[0], RestPyRequestMethodException)
        assert transport.calls == []

    def test_unregistered_url(self, mock_api, transport):
        response = mock_api.get("mock_url_that_does_not_exist")
        assert response.status_code is None
        assert len(response.errors) == 1
        assert isinstance(response.errors[0], RestPyURLNotFoundException)
        assert transport.calls == []
