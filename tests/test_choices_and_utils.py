from http import HTTPMethod

import pytest
import requests

from restpy import DataTypeChoice, RequestMethodChoice, classproperty
from restpy.exceptions import (
    RestPyIsClientErrorResponse,
    RestPyIsInformationalResponse,
    RestPyIsRedirectResponse,
    RestPyIsServerErrorResponse,
    RestPyIsSuccessResponse,
    RestPyIsValidStatusResponse,
    RestPyRunnerException,
)
from tests.conftest import FakeResponse


class TestDataTypeChoice:
    def test_json_request_is_serialised_with_its_content_type(self):
        headers, body = DataTypeChoice.parse_request(DataTypeChoice.JSON, {"a": 1})
        assert headers == {"Content-Type": "application/json"}
        assert body == '{"a": 1}'

    @pytest.mark.parametrize("data_type", [DataTypeChoice.DICT, DataTypeChoice.TEXT, DataTypeChoice.XML])
    def test_other_request_types_are_sent_as_given(self, data_type):
        assert DataTypeChoice.parse_request(data_type, {"a": 1}) == ({}, {"a": 1})

    def test_no_content_status_returns_the_text(self):
        assert DataTypeChoice.parse_response(DataTypeChoice.JSON, FakeResponse(204, text="ignored")) == "ignored"

    def test_empty_body_returns_the_text(self):
        assert DataTypeChoice.parse_response(DataTypeChoice.JSON, FakeResponse(200)) == ""

    def test_invalid_json_falls_back_to_the_text(self):
        assert DataTypeChoice.parse_response(DataTypeChoice.JSON, FakeResponse(200, text="not json")) == "not json"

    def test_json_array_is_parsed(self):
        assert DataTypeChoice.parse_response(DataTypeChoice.JSON, FakeResponse(200, [{"a": 1}])) == [{"a": 1}]

    def test_members_compare_equal_to_their_value(self):
        assert DataTypeChoice.JSON == "json"
        assert DataTypeChoice("xml") is DataTypeChoice.XML

    def test_token_is_read_from_a_json_key(self):
        assert DataTypeChoice.get_token(FakeResponse(200, {"token": "abc"}), "json", "token") == "abc"

    def test_token_is_read_from_an_attribute(self):
        assert DataTypeChoice.get_token(FakeResponse(200, text="abc"), "text", "ignored") == "abc"


class TestRequestMethodChoice:
    def test_without_a_session_it_resolves_against_requests(self):
        assert RequestMethodChoice.request(HTTPMethod.GET) is requests.get
        assert RequestMethodChoice.request(HTTPMethod.DELETE) is requests.delete

    def test_with_a_session_it_resolves_against_the_session(self):
        with requests.Session() as session:
            assert RequestMethodChoice.request(HTTPMethod.POST, session=session) == session.post

    @pytest.mark.parametrize("method", [HTTPMethod.HEAD, HTTPMethod.OPTIONS, HTTPMethod.PUT, HTTPMethod.PATCH])
    def test_every_supported_verb_is_mapped(self, method):
        assert callable(RequestMethodChoice.request(method))


class TestClassProperty:
    def test_it_is_readable_from_the_class_and_from_an_instance(self):
        class Example:
            @classproperty
            def label(cls):
                return f"label-{cls.__name__}"

        assert Example.label == "label-Example"
        assert Example().label == "label-Example"

    def test_subclasses_receive_their_own_class(self):
        class Base:
            @classproperty
            def label(cls):
                return cls.__name__

        class Child(Base): ...

        assert Child.label == "Child"

    def test_getter_replaces_the_function(self):
        prop = classproperty()
        prop.getter(lambda cls: "replaced")
        assert prop.__get__(None, object) == "replaced"


class TestStatusRunners:
    @pytest.mark.parametrize(
        ("runner", "ok_status", "bad_status"),
        [
            (RestPyIsInformationalResponse, 101, 200),
            (RestPyIsSuccessResponse, 204, 404),
            (RestPyIsRedirectResponse, 301, 200),
            (RestPyIsClientErrorResponse, 404, 500),
            (RestPyIsServerErrorResponse, 503, 404),
        ],
    )
    def test_runner_flags_only_statuses_outside_its_class(self, runner, ok_status, bad_status):
        assert runner.validate(FakeResponse(ok_status)) is None
        assert isinstance(runner.validate(FakeResponse(bad_status)), runner)

    def test_valid_status_runner_uses_the_given_list(self):
        assert RestPyIsValidStatusResponse.validate(FakeResponse(200), valid_status=[200, 201]) is None
        assert isinstance(RestPyIsValidStatusResponse.validate(FakeResponse(202), valid_status=[200, 201]), RestPyIsValidStatusResponse)

    def test_validate_can_raise(self):
        with pytest.raises(RestPyIsSuccessResponse):
            RestPyIsSuccessResponse.validate(FakeResponse(500), raise_exception=True)

    def test_message_names_the_failed_check(self):
        exception = RestPyIsSuccessResponse.validate(FakeResponse(500))
        assert "NO Success response" in exception.message
        assert repr(exception) == exception.message

    def test_a_runner_without_a_check_cannot_validate(self):
        with pytest.raises(NotImplementedError):
            RestPyRunnerException.validate(FakeResponse(200))
