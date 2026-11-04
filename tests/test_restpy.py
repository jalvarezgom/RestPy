from http import HTTPMethod

import pytest

from restpy import RestPyURL

ACCOUNT_URL = "/riot/account/v1/accounts/me"


class TestRestPy:
    def test_init(self, api):
        assert api
        assert api.auth_module
        assert api.auth_module.raw_token is not None

    def test_register(self, api):
        api.register(name="me_register", url=ACCOUNT_URL, request_methods=[HTTPMethod.GET])
        url = api.registered_urls.get("me_register", None)
        assert isinstance(url, RestPyURL)
        assert url.name == "me_register"
        assert url.url == ACCOUNT_URL

    def test_duplicated_register(self, api):
        api.register(name="me_duplicated", url=ACCOUNT_URL, request_methods=[HTTPMethod.GET])
        with pytest.raises(ValueError):
            api.register(name="me_duplicated", url=ACCOUNT_URL, request_methods=[HTTPMethod.GET])

    def test_search_url(self, api):
        api.register(name="me_search", url=ACCOUNT_URL, request_methods=[HTTPMethod.GET])
        by_name = api.search_url(name="me_search")
        assert isinstance(by_name, RestPyURL)
        assert by_name.name == "me_search"
        assert by_name.url == ACCOUNT_URL
        by_url = api.search_url(url_str=ACCOUNT_URL)
        assert by_url is by_name
