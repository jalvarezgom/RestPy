import json
from enum import StrEnum
from xml.parsers.expat import ExpatError

import xmltodict

from restpy.exceptions.request import RestPyResponseTypeException


class DataTypeChoice(StrEnum):
    """Body formats. `JSON`, `XML` and `TEXT` apply to responses; `JSON` and `DICT` to requests.

    `DICT` sends the params as a form body and is not valid as a response type.
    """

    JSON = "json"
    XML = "xml"
    TEXT = "text"
    DICT = "dict"

    @staticmethod
    def parse_request(response_type, data):
        """Return `(extra_headers, body)` for a request: JSON-encoded for `JSON`, untouched otherwise."""
        if response_type == DataTypeChoice.JSON:
            return ({"Content-Type": "application/json"}, json.dumps(data))
        else:
            return ({}, data)

    @staticmethod
    def parse_response(response_type, response):
        """Parse a response body.

        An empty body or a 204 returns the text. JSON and XML fall back to the raw text when
        they cannot be parsed.

        Raises:
            RestPyResponseTypeException: For a type that cannot describe a response.
        """
        if response.status_code == 204 or not response.text:
            return response.text
        elif response_type == DataTypeChoice.JSON:
            try:
                return response.json()
            except ValueError:
                return response.text
        elif response_type == DataTypeChoice.XML:
            try:
                return xmltodict.parse(response.text)
            except ExpatError:
                return response.text
        elif response_type == DataTypeChoice.TEXT:
            return response.text
        else:
            raise RestPyResponseTypeException("Response type not supported")

    @staticmethod
    def get_token(response, get_token_method, get_token_key):
        """Read a token from a login response: the `get_token_method` attribute, or a JSON key when it is "json"."""
        token = getattr(response, get_token_method)
        if get_token_method == DataTypeChoice.JSON:
            token = token().get(get_token_key)
        return token
