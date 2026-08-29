from http import HTTPMethod

import pytest
import requests

from restpy import RestPy, RestPyAuthDisabled, RestPyURL
from restpy.exceptions.request import RestPyRequestMethodException, RestPyURLNotFoundException
from restpy.exceptions.status_codes import RestPyIsSuccessResponse
from restpy.exceptions.validators import RestPyValidatorException
from restpy.validators import NumberValidator, StrValidator

BASE_URL = "https://pokeapi.co/api/v2"


def _is_pokeapi_online():
    try:
        requests.head(BASE_URL + "/pokemon/ditto", timeout=5)
    except requests.RequestException:
        return False
    return True


pytestmark = pytest.mark.skipif(not _is_pokeapi_online(), reason="PokeAPI no esta accesible desde este entorno")


class PokeAPI(RestPy):
    # [AUTH] API publica: no requiere credenciales
    auth_module = RestPyAuthDisabled()

    def register_urls(self):
        self.register(
            name="pokeapi_pokemon_by_name",
            url="/pokemon/{name}",
            request_methods=[HTTPMethod.GET],
            url_params=[{"name": "name", "is_required": True, "validator": StrValidator()}],
        )
        self.register(
            name="pokeapi_pokemon_list",
            url="/pokemon",
            request_methods=[HTTPMethod.GET],
            query_params=[
                {"name": "limit", "is_required": True, "validator": NumberValidator()},
                {"name": "offset", "validator": NumberValidator()},
            ],
        )
        self.register(
            name="pokeapi_ability_by_id",
            url="/ability/{id}",
            request_methods=[HTTPMethod.GET],
            url_params=[{"name": "id", "is_required": True, "validator": StrValidator()}],
        )


@pytest.fixture(scope="module")
def poke_api():
    return PokeAPI(base_url=BASE_URL)


class TestRPYPokeAPI:
    def test_registered_urls(self, poke_api):
        url = poke_api.search_url(name="pokeapi_pokemon_by_name")
        assert isinstance(url, RestPyURL)
        assert url.url == "/pokemon/{name}"
        assert list(url.url_fields) == ["name"]
        assert sorted(poke_api.search_url(name="pokeapi_pokemon_list").query_fields) == ["limit", "offset"]

    def test_get_with_url_params(self, poke_api):
        response = poke_api.get("pokeapi_pokemon_by_name", url_params={"name": "ditto"})
        assert response.errors is None
        assert response.status_code == 200
        assert response.url == f"{BASE_URL}/pokemon/ditto"
        assert response.data["name"] == "ditto"
        assert response.data["id"] == 132

    def test_get_with_query_params(self, poke_api):
        response = poke_api.get("pokeapi_pokemon_list", query_params={"limit": 5, "offset": 20})
        assert response.errors is None
        assert response.status_code == 200
        assert len(response.data["results"]) == 5
        assert response.data["count"] > 5

    def test_get_casts_url_param_with_validator(self, poke_api):
        # StrValidator convierte el numero a str para poder formatear la URL
        response = poke_api.get("pokeapi_ability_by_id", url_params={"id": 1})
        assert response.errors is None
        assert response.status_code == 200
        assert response.data["name"] == "stench"

    def test_get_missing_required_url_param(self, poke_api):
        response = poke_api.get("pokeapi_pokemon_by_name", url_params={})
        assert response.status_code is None
        assert len(response.errors) == 1
        assert isinstance(response.errors[0], RestPyValidatorException)

    def test_get_invalid_query_param_type(self, poke_api):
        response = poke_api.get("pokeapi_pokemon_list", query_params={"limit": 5, "offset": "veinte"})
        assert response.status_code is None
        assert len(response.errors) == 1
        assert isinstance(response.errors[0], RestPyValidatorException)

    def test_get_not_found_status(self, poke_api):
        response = poke_api.get("pokeapi_pokemon_by_name", url_params={"name": "pokemon-que-no-existe"})
        assert response.status_code == 404
        assert len(response.errors) == 1
        assert isinstance(response.errors[0], RestPyIsSuccessResponse)

    def test_request_method_not_allowed(self, poke_api):
        response = poke_api.post("pokeapi_pokemon_by_name", url_params={"name": "ditto"})
        assert response.status_code is None
        assert len(response.errors) == 1
        assert isinstance(response.errors[0], RestPyRequestMethodException)

    def test_unregistered_url(self, poke_api):
        response = poke_api.get("pokeapi_url_inexistente")
        assert response.status_code is None
        assert len(response.errors) == 1
        assert isinstance(response.errors[0], RestPyURLNotFoundException)
