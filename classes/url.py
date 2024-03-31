from enum import StrEnum
from functools import cached_property
from http import HTTPMethod
from typing import Dict

from validators.base import BaseValidator

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
    _used_names = set()

    def __init__(
        self,
        name: str = None,
        url: str = "",
        request_methods: list[HTTPMethod] = ALL_REQUEST_METHODS,
        url_params: list = [],
        query_params: list = [],
        data_params: list = [],
    ):
        if name in self._used_names:
            raise ValueError(f"[RestPyURL] Name {name} is already used.")
        else:
            self._used_names.add(name)
        self.name: str = name
        self.url: str = url
        self.request_methods: list[HTTPMethod] = request_methods
        self._fields: Dict[str, RESTpyField] = {}
        for url_param in url_params:
            field = RESTpyField(where_data=RestPyFieldWhereData.URL_PARAMS, **url_param)
            self._fields[field.name] = field
        for query_param in query_params:
            field = RESTpyField(where_data=RestPyFieldWhereData.QUERY_PARAMS, **query_param)
            self._fields[field.name] = field
        for dat in data_params:
            field = RESTpyField(where_data=RestPyFieldWhereData.BODY, **dat)
            self._fields[field.name] = field

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


