import logging
from http import HTTPStatus, HTTPMethod
from logging import Logger
from typing import List, Dict

from classes.url import RestPyURL
from auth.auth import RestPyAuthModule
from choices.data_type import DataTypeChoice
from classes.response import RESTpyResponse
from exceptions.auth import RestPyAuthException
from exceptions.base import RestPyRunnerException
from exceptions.request import RestPyRequestMethodException
from exceptions.status_codes import RestPyLoginException


class RestPyModule:
    # [AUTH]
    auth_module: RestPyAuthModule = None

    # [Actions]
    RETRIES_URL = 3
    RETRIES_TIMEOUT_SECONDS = 1
    RETRIES_STATUS_CODES = [HTTPStatus.REQUEST_TIMEOUT, HTTPStatus.GATEWAY_TIMEOUT]
    REFRESH_LOGIN_STATUS_CODES = [HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN]
    _base_url: str = None

    # TODO: Refactorizar a entidad
    # endpoint_url = None
    # params_fields: dict = {}
    # data_fields: dict = {}
    # request_data_type = DataTypeChoice.DICT
    _response_data_type = DataTypeChoice.JSON
    _response_manager = RESTpyResponse

    # [Validators]
    _EXCEPTION_VALID_STATUS_RUNNER = []
    _EXCEPTION_VALID_RESPONSE_RUNNER = []
    _VALID_STATUS = [
        HTTPStatus.OK,
        HTTPStatus.CREATED,
        HTTPStatus.NO_CONTENT,
        HTTPStatus.RESET_CONTENT,
    ]  # https://docs.python.org/3/library/http.html#http-status-codes

    # [Others]
    headers: dict = None
    _logger: Logger = None

    def __init__(self, base_url: str = None, auth_action: RestPyAuthModule = None):
        self.registered_urls: Dict[str, RestPyURL] = {}
        self.__registered_urls_list: List[RestPyURL] = []
        self._base_url: str = base_url
        self.headers = {}
        if auth_action and not (isinstance(auth_action, RestPyAuthModule)):
            raise ValueError("auth_action must be an instance of RestPyAuth or a dictionary with the auth parameters.")
        self.auth_module: RestPyAuthModule = auth_action

    # [Properties]
    @property
    def name(self):
        return self.__class__.__name__

    @property
    def base_url(self):
        return self._base_url

    @property
    def auth_headers(self):
        return self.auth_module.auth_headers

    @property
    def logger(self):
        if not self._logger:
            self._logger = logging.getLogger("restpy")
            if not self._logger.hasHandlers():
                self._logger = logging.getLogger()
        return self._logger

    @property
    def is_logger_functional(self):
        return self.logger.hasHandlers()

    # [Authentication]
    def set_auth(self, auth_action):
        if not isinstance(auth_action, RestPyAuthModule):
            raise ValueError("auth_action must be an instance of RestPyAuth")
        self.auth_module = auth_action

    def login(self, refresh=False):
        if not self.auth_module:
            raise RestPyAuthException('You must define "auth_module" variable with a valid RESTpyAuth class.')
        status = True
        if refresh or not self.auth_module.token:
            status = self.auth_module.login(refresh=refresh)
            if not status and refresh:
                raise RestPyLoginException(self.name)
            if not status:
                self.logger.error(f"{RestPyLoginException(self.name)} | Login failed, a refresh is needed ")
        self.auth_module.generate_auth_headers()
        return status

    # [API]
    def set_base_url(self, base_url: str):
        self._base_url = base_url

    def register(
        self,
        name: str = None,
        url: str = None,
        request_methods: List[HTTPMethod] = [],
        url_params: List[Dict] = [],
        query_params: List[Dict] = [],
    ):
        if not url or not isinstance(url, str):
            raise ValueError("url is required with type str.")
        if not request_methods or not isinstance(request_methods, List):
            raise ValueError("request_methods is required with type List[HTTPMethod]")
        if not all([isinstance(method, HTTPMethod) for method in request_methods]):
            raise ValueError("request_methods must be a list of HTTPMethod instances.")
        if not all([isinstance(param, dict) for param in url_params]):
            raise ValueError("url_params must be a list of dictionaries.")
        if not all([isinstance(param, dict) for param in query_params]):
            raise ValueError("query_params must be a list of dictionaries.")
        if name in self.registered_urls:
            raise ValueError(f"Name {name} is already registered in {self.name}.")
        rp_url = RestPyURL(name=name, url=url, request_methods=request_methods, url_params=url_params, query_params=query_params)
        self.registered_urls[name] = rp_url
        self.__registered_urls_list.append(rp_url)

    def search_url(self, *, name: str = None, url_str: str = None):
        if name:
            url = self.__search_url_by_name(name)
        elif url_str:
            url = self.__search_url_by_url(url_str)
        else:
            raise ValueError("name or url_str is required.")
        if not url:
            self.logger.debug(f"[{self.name}] RestPyURL not found. Params: Name {name} - URL: {url} ")
        return url

    def __search_url_by_name(self, name: str):
        return self.registered_urls.get(name, None)

    def __search_url_by_url(self, url: str):
        return next((rp_url for rp_url in self.registered_urls if rp_url.url == url), None)

    # [Actions]
    def get(self, name: str = None, url_str: str = None, url_params={}, query_params={}, **xtra_params):
        return self._emit_request(HTTPMethod.GET, name=name, url_str=url_str, url_params=url_params, query_params=query_params, **xtra_params)

    def post(self, name: str = None, url_params={}, query_params={}, data={}, **xtra_params):
        return self._emit_request(HTTPMethod.POST, name=name, url_params=url_params, query_params=query_params, data=data, **xtra_params)

    def put(self, name: str = None, url_params={}, query_params={}, data={}, **xtra_params):
        return self._emit_request(HTTPMethod.PUT, name=name, url_params=url_params, query_params=query_params, data=data, **xtra_params)

    def patch(self, name: str = None, url_params={}, query_params={}, data={}, **xtra_params):
        return self._emit_request(HTTPMethod.PATCH, name=name, url_params=url_params, query_params=query_params, data=data, **xtra_params)

    def delete(self, name: str = None, url_params={}, query_params={}, data={}, **xtra_params):
        return self._emit_request(HTTPMethod.DELETE, name=name, url_params=url_params, query_params=query_params, data=data, **xtra_params)

    def _emit_request(self, request_method: HTTPMethod, name: str = None, url_str: str = None, url_params={}, query_params={}, **xtra_params):
        errors = []
        url: RestPyURL | None = self.search_url(name=name, url_str=url_str)
        # Validar request method
        field_errors = self._validate_request_method(request_method, url)
        # Validar la peticion

        if field_errors:
            self.logger.error(f"[{self.name}] Error in request - {field_errors}")
            return self._prepare_response(None, field_errors)

        counter_request = 0
        while counter_request < self.RETRIES_URL:
            response = self._send_request(request_method, url, url_params, query_params, **xtra_params)
            counter_request += 1
            if self.__check_login_action(response):
                self.logger.info(f"[{self.name}] Login refreshed")
                self.login(refresh=True)
                continue
            if not self.__check_retry_action(response):
                break
            self.logger.debug(f"[{self.name}] Retry {counter_request} - {response.status_code}")
        # Validamos status
        field_errors = self._validate_response_status(response)
        if field_errors:
            return self._prepare_response(None, field_errors)
        # Validamos la response
        field_errors = self.validate_response_data(response)
        if field_errors:
            return self._prepare_response(None, field_errors)
        return self._prepare_response(response, None)

    def _send_request(self, request_method, url, params, data):
        return {}

    def __check_login_action(self, response):
        return response.status_code in self.REFRESH_LOGIN_STATUS_CODES

    def __check_retry_action(self, response):
        return response.status_code in self.RETRIES_STATUS_CODES

    def _prepare_response(self, response, field_errors):
        if field_errors:
            return self._response_manager(response, None, field_errors)
        return self._response_manager(response, DataTypeChoice.parse_response(self._response_data_type, response), None)

    # [Validators]
    def _validate_request_method(self, request_method, url):
        exception = RestPyRequestMethodException.validate(request_method, url=url)
        if exception:
            return [exception]
        return []

    # TODO: Refactorizar el  validador de fields de la request
    # def _validate_request_fields(self, request_method, params, validation_fields={}, **xtra_params):
    #     field_errors = []
    #     if request_method not in self.valid_request_methods:
    #         field_errors.append(RESTpyValidatorRequestMethodException(request_method))
    #     for field, field_param in validation_fields.items():
    #         _, exception_required = RequiredFieldValidator.validate(field_param, (field, params))
    #         value, exception_validator = field_param.validator.validate(field, params.get(field, None))
    #         if exception_required:
    #             field_errors.append(exception_required)
    #         if exception_validator:
    #             field_errors.append(exception_validator)
    #         elif value:
    #             params[field] = value
    #     return field_errors

    def _validate_response_status(self, response, **xtra_params):
        list_exceptions = []
        if response.status_code not in self._VALID_STATUS:
            for exception in self._validator_runner(self._EXCEPTION_VALID_STATUS_RUNNER, response):
                if exception:
                    list_exceptions.append(exception)
                    break
        if all([self._response_data_type == DataTypeChoice.JSON, not response.text.startswith("{")]):
            response.status_code = HTTPStatus.NO_CONTENT
            self.logger.debug(f"[{self.name}] WARNING STATUS {response.status_code} - NO CONTENT")
        return list_exceptions

    def validate_response_data(self, response, **xtra_params):
        list_exceptions = []
        for exception in self._validator_runner(self._EXCEPTION_VALID_RESPONSE_RUNNER, response):
            if exception:
                list_exceptions.append(exception)
                break
        return list_exceptions

    def add_valid_status(self, status_code):
        if not isinstance(status_code, HTTPStatus):
            raise ValueError("status_code must be an instance of HTTPStatus")
        self._VALID_STATUS.append(status_code)

    def remove_valid_status(self, status_code):
        if not isinstance(status_code, HTTPStatus):
            raise ValueError("status_code must be an instance of HTTPStatus")
        self._VALID_STATUS.remove(status_code)

    def add_exception_valid_status_runner(self, exception_runner):
        if not isinstance(exception_runner, RestPyRunnerException):
            raise ValueError("exception_runner must be an instance of RestPyRunnerException")
        self._EXCEPTION_VALID_STATUS_RUNNER.append(exception_runner)

    def remove_exception_valid_status_runner(self, exception_runner):
        if not isinstance(exception_runner, RestPyRunnerException):
            raise ValueError("exception_runner must be an instance of RestPyRunnerException")
        self._EXCEPTION_VALID_STATUS_RUNNER.remove(exception_runner)

    def add_exception_valid_response_runner(self, exception_runner):
        if not isinstance(exception_runner, RestPyRunnerException):
            raise ValueError("exception_runner must be an instance of RestPyRunnerException")
        self._EXCEPTION_VALID_RESPONSE_RUNNER.append(exception_runner)

    def remove_exception_valid_response_runner(self, exception_runner):
        if not isinstance(exception_runner, RestPyRunnerException):
            raise ValueError("exception_runner must be an instance of RestPyRunnerException")
        self._EXCEPTION_VALID_RESPONSE_RUNNER.remove(exception_runner)

    def _validator_runner(self, validations_to_run, response, **xtra_params):
        for exception_runner in validations_to_run:
            exception = exception_runner.validate(response)
            yield exception
