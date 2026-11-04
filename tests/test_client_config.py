from http import HTTPMethod, HTTPStatus

import pytest
import requests

from restpy import RESTpyField, RestPy, RestPyAuthDisabled
from restpy.exceptions import (
    RestPyAuthException,
    RestPyIsServerErrorResponse,
    RestPyIsSuccessResponse,
    RestPyRunnerException,
)
from tests.conftest import FakeResponse


def make_api(**kwargs):
    kwargs.setdefault("base_url", "https://cfg.test")
    kwargs.setdefault("auth_action", RestPyAuthDisabled())
    return RestPy(**kwargs)


class RejectBadBody(RestPyRunnerException):
    base_message = "Bad body"

    @classmethod
    def _validation(cls, response, **xtra_params):
        return response.text == "bad"


class TestAuthConfiguration:
    def test_invalid_auth_action_is_rejected_at_init(self):
        with pytest.raises(ValueError):
            RestPy(base_url="https://cfg.test", auth_action="token")

    def test_set_auth_replaces_the_module(self):
        api = make_api()
        new_auth = RestPyAuthDisabled()
        api.set_auth(new_auth)
        assert api.auth_module is new_auth

    def test_set_auth_rejects_other_types(self):
        with pytest.raises(ValueError):
            make_api().set_auth({"token": "x"})

    def test_request_without_auth_module_raises(self):
        api = RestPy(base_url="https://cfg.test")
        api.register(name="ping", url="/ping", request_methods=[HTTPMethod.GET])
        with pytest.raises(RestPyAuthException):
            api.get("ping")


class TestBaseUrl:
    def test_base_url_params_given_at_init_apply_to_every_endpoint(self, transport):
        api = make_api(base_url="https://{region}.cfg.test", base_url_params=[{"name": "region", "is_required": True}])
        api.register(name="ping", url="/ping", request_methods=[HTTPMethod.GET])
        api.get("ping", url_params={"region": "eu"})
        assert transport.last_call.url == "https://eu.cfg.test/ping"

    def test_set_base_url_swaps_only_the_url(self, transport):
        api = make_api()
        api.register(name="ping", url="/ping", request_methods=[HTTPMethod.GET])
        api.set_base_url("https://other.test")
        api.get("ping")
        assert transport.last_call.url == "https://other.test/ping"

    def test_set_base_url_with_params_updates_registered_endpoints(self, transport):
        api = make_api()
        api.register(name="ping", url="/ping", request_methods=[HTTPMethod.GET])
        api.set_base_url("https://{zone}.cfg.test", base_url_params=[{"name": "zone", "is_required": True}])
        assert list(api.registered_urls) == ["ping"]
        assert api.get("ping").errors, "the new required placeholder is enforced"
        assert transport.calls == []
        api.get("ping", url_params={"zone": "us"})
        assert transport.last_call.url == "https://us.cfg.test/ping"


class TestRegisterValidation:
    @pytest.fixture
    def api(self):
        return make_api()

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"url": ""},
            {"url": 5},
            {"request_methods": []},
            {"request_methods": ["GET"]},
            {"url_params": ["id"]},
            {"query_params": ["q"]},
            {"data_params": ["d"]},
            {"request_data_type": "yaml"},
            {"response_data_type": "yaml"},
        ],
    )
    def test_invalid_arguments_are_rejected(self, api, kwargs):
        arguments = {"name": "x", "url": "/x", "request_methods": [HTTPMethod.GET], **kwargs}
        with pytest.raises(ValueError):
            api.register(**arguments)

    def test_duplicate_name_is_rejected(self, api):
        api.register(name="x", url="/x", request_methods=[HTTPMethod.GET])
        with pytest.raises(ValueError):
            api.register(name="x", url="/y", request_methods=[HTTPMethod.GET])

    def test_search_needs_a_name_or_a_path(self, api):
        with pytest.raises(ValueError):
            api.search_url()


class TestStatusConfiguration:
    def test_added_status_becomes_valid(self, transport):
        api = make_api()
        api.register(name="ping", url="/ping", request_methods=[HTTPMethod.GET])
        transport.queue(FakeResponse(304))
        assert api.get("ping").errors
        api.add_valid_status(HTTPStatus.NOT_MODIFIED)
        transport.queue(FakeResponse(304))
        assert api.get("ping").errors is None

    def test_removed_status_stops_being_valid(self, transport):
        api = make_api()
        api.register(name="ping", url="/ping", request_methods=[HTTPMethod.GET])
        api.remove_valid_status(HTTPStatus.CREATED)
        api.add_exception_valid_status_runner(RestPyIsServerErrorResponse)
        transport.queue(FakeResponse(201))
        assert api.get("ping").errors

    @pytest.mark.parametrize("method", ["add_valid_status", "remove_valid_status"])
    def test_only_http_status_members_are_accepted(self, method):
        with pytest.raises(ValueError):
            getattr(make_api(), method)(200)

    def test_no_content_is_a_valid_response(self, transport):
        api = make_api()
        api.register(name="gone", url="/gone", request_methods=[HTTPMethod.DELETE])
        transport.queue(FakeResponse(204))
        response = api.delete("gone")
        assert response.status_code == 204
        assert response.errors is None


class TestRunnerConfiguration:
    @pytest.mark.parametrize(
        "method",
        [
            "add_exception_valid_status_runner",
            "remove_exception_valid_status_runner",
            "add_exception_valid_response_runner",
            "remove_exception_valid_response_runner",
        ],
    )
    @pytest.mark.parametrize("invalid", [RestPyIsSuccessResponse(), "runner", ValueError])
    def test_only_runner_subclasses_are_accepted(self, method, invalid):
        with pytest.raises(ValueError):
            getattr(make_api(), method)(invalid)

    def test_status_runner_can_be_removed(self, transport):
        api = make_api()
        api.register(name="ping", url="/ping", request_methods=[HTTPMethod.GET])
        api.remove_exception_valid_status_runner(RestPyIsSuccessResponse)
        transport.queue(FakeResponse(404))
        # Without runners a status outside _VALID_STATUS is not flagged by anything.
        assert api.get("ping").errors is None

    def test_response_runner_reports_a_bad_body(self, transport):
        api = make_api()
        api.register(name="ping", url="/ping", request_methods=[HTTPMethod.GET], response_data_type="text")
        api.add_exception_valid_response_runner(RejectBadBody)
        transport.queue(FakeResponse(200, text="bad"), FakeResponse(200, text="fine"))
        assert isinstance(api.get("ping").errors[0], RejectBadBody)
        assert api.get("ping").errors is None

    def test_response_runner_can_be_removed(self, transport):
        api = make_api()
        api.register(name="ping", url="/ping", request_methods=[HTTPMethod.GET], response_data_type="text")
        api.add_exception_valid_response_runner(RejectBadBody)
        api.remove_exception_valid_response_runner(RejectBadBody)
        transport.queue(FakeResponse(200, text="bad"))
        assert api.get("ping").errors is None


class TestSession:
    def test_the_session_is_created_once(self):
        api = make_api()
        assert api.session is api.session
        assert isinstance(api.session, requests.Session)

    def test_close_releases_the_session_and_the_client_stays_usable(self):
        api = make_api()
        first = api.session
        api.close()
        assert api._session is None
        assert api.session is not first

    def test_close_without_a_session_is_harmless(self):
        make_api().close()

    def test_context_manager_closes_on_exit(self):
        with make_api() as api:
            assert api.session is not None
        assert api._session is None


class TestFieldDeclaration:
    """`RESTpyField` rejects malformed declarations when the endpoint is registered."""

    @pytest.mark.parametrize(
        "field",
        [
            {"name": ""},
            {"name": "id", "is_required": "yes"},
            {"name": "id", "allow_empty": 1},
            {"name": "id", "validator": object()},
            {"name": "id", "validator": str},
        ],
    )
    def test_invalid_field_is_rejected(self, field):
        with pytest.raises(ValueError):
            make_api().register(name="x", url="/x/{id}", request_methods=[HTTPMethod.GET], url_params=[field])

    def test_where_data_is_required(self):
        with pytest.raises(ValueError):
            RESTpyField(where_data=None, name="id")

    def test_unknown_field_is_not_found(self):
        api = make_api()
        api.register(name="x", url="/x", request_methods=[HTTPMethod.GET])
        assert api.search_url(name="x").get_field("missing") is None


class TestPartialURLParams:
    def test_a_missing_placeholder_is_named_in_the_error(self, transport):
        api = make_api()
        api.register(
            name="item",
            url="/users/{user}/items/{item}",
            request_methods=[HTTPMethod.GET],
            url_params=[{"name": "user"}, {"name": "item"}],
        )
        response = api.get("item", url_params={"user": 7})
        assert "item" in str(response.errors[0])
        assert transport.calls == []


class TestResponseRepresentation:
    def test_str_summarises_the_response(self, transport):
        api = make_api()
        api.register(name="ping", url="/ping", request_methods=[HTTPMethod.GET])
        transport.queue(FakeResponse(200, {"ok": True}))
        text = str(api.get("ping"))
        assert "status_code=200" in text and "'ok': True" in text
