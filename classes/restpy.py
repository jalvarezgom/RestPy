import json
import logging

from auth.auth import RESTpyAuth
from choices.request_method import RequestMethod
from choices.response_type import RequestDataType
from exceptions.auth import RESTpyAuthException
from exceptions.status_codes import RESTpyForbiddenException, RESTpyInternalServerErrorException, \
    RESTpyStatusCodeException, RESTpyLoginException
from validators.required_field import RequiredFieldValidator


class RESTpyResponse:
    _response = None
    _data = None
    _processed_data = None
    errors = None
    status_code = None

    def __init__(self, response, data=None, errors=None):
        self._response = response
        self._data = data
        self._parse_data(data)
        self.errors = errors

    @property
    def data(self):
        if not self._processed_data:
            self._processed_data = self._parse_data(self._data) if self.response else None
        return self._processed_data

    def _parse_data(self, data):
        self._processed_data = None
        if self.status_code == 200:
            self._processed_data = data


    @property
    def url(self):
        return self.response.url if self.response else None

    @property
    def response(self):
        return self._response

    @property
    def status_code(self):
        return self.response.status_code if self.response else None

    def __str__(self):
        return f'RESTpyResponse(url={self.url}, status_code={self.status_code}, data={self.data}, errors={self.errors})'

class RESTpy():
    # [AUTH]
    auth_action: RESTpyAuth = None
    _auth_headers = None

    # [API]
    headers = {}
    base_url = None
    endpoint_url = None
    request_method = None
    params_fields: dict = {}
    data_fields: dict = {}

    request_data_type = RequestDataType.DICT
    response_data_type = RequestDataType.JSON
    response_manager = RESTpyResponse

    _logger = None

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def auth_headers(self):
        return self._auth_headers

    @property
    def endpoint(self):
        params = self._get_xtra_params()
        return f'{self.base_url}/{self.endpoint_url}'.format(**params)

    def _get_xtra_params(self):
        return {}

    @property
    def logger(self):
        if not self._logger:
            self._logger = logging.getLogger()
        return self._logger

    def login(self):
        return self._login()

    def _login(self, refresh=False):
        if not self.auth_action:
            raise RESTpyAuthException('You must define "auth_action" variable with a valid RESTpyAuth class.')
        status = True
        if refresh or not self.auth_action.token:
            status = self.auth_action.login(refresh=refresh)
            if not status and refresh:
                raise RESTpyLoginException(self.name)
            if not status:
                self.logger.error(f'{RESTpyLoginException(self.name)} | Refresh is needed ')
        self._auth_headers = self.auth_action.generate_auth_headers()
        return status

    def _send_request(self, url, params, data):
        query_params_url, params = self._generate_query_params_url(params)
        query_params_url = f'/{query_params_url}' if query_params_url else ''
        if self._auth_headers:
            self.headers.update(self._auth_headers)
        _headers, _data = RequestDataType.parse_request(data, self.request_data_type)
        self.headers.update(_headers)
        return RequestMethod.request(self.request_method)(
            url + query_params_url,
            params=params,
            data=_data,
            headers=self.headers,
            cookies=self.auth_action.cookies
        )

    def _generate_query_params_url(self, params):
        query_params_url = []
        for field, field_param in self.params_fields.items():
            if field_param.is_query_params:
                if params.get(field):
                    param = params.get(field)
                    query_params_url.append(param if param else None)
                params.pop(field, None)
        return '/'.join(query_params_url), params

    def send_request(self, params={}, data={}):
        if not self._auth_headers:
            self._login()
        field_errors = self._valid_request_params(params, self.params_fields)
        if field_errors:
            return self._prepare_response(None, field_errors)
        field_errors = self._valid_request_params(data, self.data_fields)
        if field_errors:
            return self._prepare_response(None, field_errors)
        response = self._send_request(self.endpoint, params, data)
        if response.status_code in [401, 403]:
            self._login(refresh=True)
            response = self._send_request(self.endpoint, params, data)
        field_errors = self._valid_response_status(response)
        return self._prepare_response(response, field_errors)

    def _prepare_response(self, response, field_errors):
        if field_errors:
            return self.response_manager(
                response,
                None,
                field_errors
            )
        return self.response_manager(
            response,
            RequestDataType.parse_response(response, self.response_data_type),
            None
        )

    def _valid_request_params(self, params, validation_fields={}):
        field_errors = []
        for field, field_param in validation_fields.items():
            _, exception_required = RequiredFieldValidator.validate(field_param, (field, params))
            value, exception_validator = field_param.validator.validate(field, params.get(field, None))
            if exception_required:
                field_errors.append(exception_required)
            if exception_validator:
                field_errors.append(exception_validator)
            elif value:
                params[field] = value
        return field_errors

    def _valid_response_status(self, response):
        if all([self.response_data_type == RequestDataType.JSON, response.status_code == 200, not response.text.startswith('{')]):
            response.status_code = 204
            self.logger.warning(f"[{self.__class__.__name__}] WARNING STATUS {response.status_code} - NO CONTENT")
            return None
        if response.status_code in [200, 201]:
            return None
        if response.status_code == 401:
            exception = RESTpyLoginException(self.__class__.__name__)
        elif response.status_code == 403:
            exception = RESTpyForbiddenException(self.__class__.__name__)
        elif response.status_code == 500:
            exception = RESTpyInternalServerErrorException(self.__class__.__name__)
        else:
            exception = RESTpyStatusCodeException(self.__class__.__name__)
        self.logger.error(exception)
        return [exception]
