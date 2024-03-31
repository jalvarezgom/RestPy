import pytest

from http import HTTPMethod

from classes.url import RestPyURL


class TestRestPy:
    def test_init(self, api):
        assert api
        assert api.auth_module
        assert api.auth_module.raw_token is not None

    def test_register(self, api):
        api.register(
            name="me_test",
            url="/riot/account/v1/accounts/me",
            request_methods=[HTTPMethod.GET],
        )
        url = api.registered_urls.get("me_test", None)
        assert url
        assert isinstance(url, RestPyURL)
        assert url.name == "me_test"
        assert url.url == "/riot/account/v1/accounts/me"

    def test_duplicated_register(self, api):
        with pytest.raises(ValueError):
            api.register(
                name="me_test",
                url="/riot/account/v1/accounts/me",
                request_methods=[HTTPMethod.GET],
            )
            api.register(
                name="me_test",
                url="/riot/account/v1/accounts/me",
                request_methods=[HTTPMethod.GET],
            )

    def test_search_url(self, api):
        try:
            api.register(
                name="me_test",
                url="/riot/account/v1/accounts/me",
                request_methods=[HTTPMethod.GET],
            )
        except ValueError:
            pass
        url = api.search_url(name="me_test")
        assert url
        assert isinstance(url, RestPyURL)
        assert url.name == "me_test"
        assert url.url == "/riot/account/v1/accounts/me"
        url = api.search_url(url_str="/riot/account/v1/accounts/me")
        assert url
        assert isinstance(url, RestPyURL)
        assert url.name == "me_test"
        assert url.url == "/riot/account/v1/accounts/me"
