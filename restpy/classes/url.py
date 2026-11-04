from enum import StrEnum
from functools import cached_property
from http import HTTPMethod
from typing import Dict

from restpy.choices.data_type import DataTypeChoice
from restpy.classes.response import RESTpyResponse
from restpy.validators.base import BaseValidator

ALL_REQUEST_METHODS = [HTTPMethod.GET, HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.PATCH, HTTPMethod.DELETE]


class RestPyFieldWhereData(StrEnum):
    """Where a field travels in the request: the URL path, the query string or the body."""

    URL_PARAMS = "URI"
    QUERY_PARAMS = "QUERY"
    BODY = "BODY"


class RESTpyField:
    """Definition of one request parameter: its name, location, whether it is required and how it is validated."""

    def __init__(self, *, where_data: RestPyFieldWhereData, name: str, is_required=False, allow_empty=False, validator=None, **xtra_params):
        """
        Args:
            where_data: Where the field is sent.
            name: Name of the parameter.
            is_required: The field must be present and not None (or "" unless `allow_empty`).
            allow_empty: Accept "" for a required field. `None` is still rejected.
            validator: A `BaseValidator` **instance** run on the value after the required check.
            **xtra_params: Accepted and ignored, so a misspelled option raises no error.

        Raises:
            ValueError: If an argument has the wrong type or `where_data`/`name` is missing.
        """
        if not where_data:
            raise ValueError("where_data is required.")
        if not name:
            raise ValueError("name is required.")
        if is_required and not isinstance(is_required, bool):
            raise ValueError("is_required must be a boolean.")
        if not isinstance(allow_empty, bool):
            raise ValueError("allow_empty must be a boolean.")
        if validator and not isinstance(validator, BaseValidator):
            raise ValueError("validator must be an instance of BaseValidator.")
        self.where_data = where_data
        self.name = name
        self.required = is_required
        self.allow_empty = allow_empty
        self.validator = validator


class RestPyURL:
    """A registered endpoint: path, accepted verbs, data types and declared fields.

    Built by `RestPyModule.register()`; it is rarely created directly. With no
    `request_methods` it accepts every verb in `ALL_REQUEST_METHODS`.
    """

    def __init__(
        self,
        name: str = None,
        url: str = "",
        request_methods: list[HTTPMethod] = None,
        request_data_type: DataTypeChoice = None,
        url_params: list = None,
        query_params: list = None,
        data_params: list = None,
        response_data_type: DataTypeChoice = None,
        response_manager: RESTpyResponse = None,
    ):
        # Name uniqueness is owned by the client: see RestPyModule.register().
        self.name: str = name
        self.url: str = url
        self.request_methods: list[HTTPMethod] = list(request_methods) if request_methods else list(ALL_REQUEST_METHODS)
        self.request_data_type: DataTypeChoice = request_data_type
        self._fields: Dict[tuple[RestPyFieldWhereData, str], RESTpyField] = {}
        self.response_data_type: DataTypeChoice = response_data_type
        self._response_manager: RESTpyResponse = response_manager
        for url_param in url_params or []:
            field = RESTpyField(where_data=RestPyFieldWhereData.URL_PARAMS, **url_param)
            self._fields[(field.where_data, field.name)] = field
        for query_param in query_params or []:
            field = RESTpyField(where_data=RestPyFieldWhereData.QUERY_PARAMS, **query_param)
            self._fields[(field.where_data, field.name)] = field
        for dat in data_params or []:
            field = RESTpyField(where_data=RestPyFieldWhereData.BODY, **dat)
            self._fields[(field.where_data, field.name)] = field

    @property
    def response_manager(self):
        """`RESTpyResponse` subclass used to wrap this endpoint's responses."""
        return self._response_manager

    @property
    def fields_list(self):
        """Every declared field, across the three locations."""
        return self._fields.values()

    @cached_property
    def url_fields(self):
        """Fields declared for the URL path, by name."""
        return {field.name: field for field in self.fields_list if field.where_data == RestPyFieldWhereData.URL_PARAMS}

    @cached_property
    def query_fields(self):
        """Fields declared for the query string, by name."""
        return {field.name: field for field in self.fields_list if field.where_data == RestPyFieldWhereData.QUERY_PARAMS}

    @cached_property
    def data_fields(self):
        """Fields declared for the body, by name."""
        return {field.name: field for field in self.fields_list if field.where_data == RestPyFieldWhereData.BODY}

    def get_field(self, name, where_data: RestPyFieldWhereData = None):
        """Return the field called `name`, or None. Without `where_data` the first match wins."""
        if where_data is not None:
            return self._fields.get((where_data, name), None)
        return next((field for field in self.fields_list if field.name == name), None)
