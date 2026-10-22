from enum import StrEnum
from functools import cached_property
from http import HTTPMethod
from typing import Dict

from restpy.choices.data_type import DataTypeChoice
from restpy.classes.response import RESTpyResponse
from restpy.validators.base import BaseValidator

ALL_REQUEST_METHODS = [HTTPMethod.GET, HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.PATCH, HTTPMethod.DELETE]


class RestPyFieldWhereData(StrEnum):
    URL_PARAMS = "URI"
    QUERY_PARAMS = "QUERY"
    BODY = "BODY"


class RESTpyField:
    def __init__(self, *, where_data: RestPyFieldWhereData, name: str, is_required=False, validator=None, **xtra_params):
        if not where_data:
            raise ValueError("where_data is required.")
        if not name:
            raise ValueError("name is required.")
        if is_required and not isinstance(is_required, bool):
            raise ValueError("is_required must be a boolean.")
        if validator and not isinstance(validator, BaseValidator):
            raise ValueError("validator must be an instance of BaseValidator.")
        self.where_data = where_data
        self.name = name
        self.required = is_required
        self.validator = validator


class RestPyURL:
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
        self._fields: Dict[str, RESTpyField] = {}
        self.response_data_type: DataTypeChoice = response_data_type
        self._response_manager: RESTpyResponse = response_manager
        for url_param in url_params or []:
            field = RESTpyField(where_data=RestPyFieldWhereData.URL_PARAMS, **url_param)
            self._fields[field.name] = field
        for query_param in query_params or []:
            field = RESTpyField(where_data=RestPyFieldWhereData.QUERY_PARAMS, **query_param)
            self._fields[field.name] = field
        for dat in data_params or []:
            field = RESTpyField(where_data=RestPyFieldWhereData.BODY, **dat)
            self._fields[field.name] = field

    @property
    def response_manager(self):
        return self._response_manager

    @property
    def fields_list(self):
        return self._fields.values()

    @cached_property
    def url_fields(self):
        return {field.name: field for field in self.fields_list if field.where_data == RestPyFieldWhereData.URL_PARAMS}

    @cached_property
    def query_fields(self):
        return {field.name: field for field in self.fields_list if field.where_data == RestPyFieldWhereData.QUERY_PARAMS}

    @cached_property
    def data_fields(self):
        return {field.name: field for field in self.fields_list if field.where_data == RestPyFieldWhereData.BODY}

    def get_field(self, name):
        return self._fields.get(name, None)
