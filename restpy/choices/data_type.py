import json

import xmltodict

from exceptions.request import RestPyResponseTypeException


class DataTypeChoice:
    JSON = "json"
    XML = "xml"
    TEXT = "text"
    DICT = "dict"

    @staticmethod
    def parse_request(response_type, data):
        if response_type == DataTypeChoice.JSON:
            return ({"Content-Type": "application/json"}, json.dumps(data))
        else:
            return ({}, data)

    @staticmethod
    def parse_response(response_type, response):
        if any(
            [
                response.status_code == 204,
                not response.text,
                response_type == DataTypeChoice.JSON and not response.text.startswith("{"),
            ]
        ):
            return response.text
        elif response_type == DataTypeChoice.JSON:
            return response.json()
        elif response_type == DataTypeChoice.XML:
            return xmltodict.parse(response.text) if response.text else {}
        else:
            raise RestPyResponseTypeException("Response type not supported")

    @staticmethod
    def get_token(response, get_token_method, get_token_key):
        token = getattr(response, get_token_method)
        if get_token_method == DataTypeChoice.JSON:
            token = token().get(get_token_key)
        return token
