import json

import xmltodict

from exceptions.choices import RESTpyResponseTypeException


class RequestDataType:
    JSON = 'json'
    XML = 'xml'
    TEXT = 'text'
    DICT = 'dict'

    @staticmethod
    def parse_request(data, response_type):
        if response_type == RequestDataType.JSON:
            return {'Content-Type': 'application/json'}, json.dumps(data)
        else:
            return {}, data

    @staticmethod
    def parse_response(response, response_type):
        if response_type == RequestDataType.JSON:
            if response.status_code == 204 or not response.text.startswith('{'):
                return response.text
            else:
                return response.json()
        elif response_type == RequestDataType.XML:
            return xmltodict.parse(response.text)
        else:
            raise RESTpyResponseTypeException('Response type not supported')

    @staticmethod
    def get_token(response, get_token_method, get_token_key):
        token = getattr(response, get_token_method)
        if get_token_method == RequestDataType.JSON:
            token = token().get(get_token_key)
        return token
