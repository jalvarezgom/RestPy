import logging
import time
from http import HTTPStatus, HTTPMethod
from logging import Logger
from typing import List, Dict

from classes.url import RestPyURL
from auth.auth import RestPyAuthModule
from choices.data_type import DataTypeChoice
from classes.response import RESTpyResponse
from exceptions.auth import RestPyAuthException
from exceptions.base import RestPyRunnerException
from exceptions.request import RestPyRequestMethodException, RestPyURLNotFoundException
from exceptions.status_codes import RestPyLoginException, RestPyIsSuccessResponse, RestPyIsValidStatusResponse
from choices.request_method import RequestMethodChoice
from validators.required_field import RequiredFieldValidator


class RestPyModule:
    # [AUTH]
    auth_module: RestPyAuthModule = None

    # [Actions]
    RETRIES_URL = 3
    RETRIES_TIMEOUT_SECONDS = 1
    RETRIES_TIMEOUT_STATUS_CODES = [HTTPStatus.REQUEST_TIMEOUT, HTTPStatus.GATEWAY_TIMEOUT]
    RETRIES_STATUS_CODES = [HTTPStatus.REQUEST_TIMEOUT, HTTPStatus.GATEWAY_TIMEOUT]
    REFRESH_LOGIN_STATUS_CODES = [HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN]
    _base_url: str = None
    _base_url_params: list = []

    # TODO: Refactorizar a entidad
    # [Default RP Urls]
    default_request_data_type = DataTypeChoice.DICT
    default_response_data_type = DataTypeChoice.JSON
    default_response_manager = RESTpyResponse

    # [Validators]
    _EXCEPTION_VALID_STATUS_RUNNER = [RestPyIsSuccessResponse]
    _EXCEPTION_VALID_RESPONSE_RUNNER = []
    _VALID_STATUS = [
        HTTPStatus.OK,
        HTTPStatus.CREATED,
        HTTPStatus.NO_CONTENT,
        HTTPStatus.RESET_CONTENT,
    ]  # https://docs.python.org/3/library/http.html#http-status-codes

    # [Others]
    headers: dict = {}
    _logger: Logger = None

    def __init__(self, headers: dict = None, base_url: str = None, base_url_params: list = None, auth_action: RestPyAuthModule = None):
        self.registered_urls: Dict[str, RestPyURL] = {}
        self.__registered_urls_list: List[RestPyURL] = []
        if headers:
            self.headers = headers
        if base_url:
            self._base_url = base_url
        if base_url_params:
            self._base_url_params: list = base_url_params
        if auth_action and not (isinstance(auth_action, RestPyAuthModule)):
            raise ValueError("auth_action must be an instance of RestPyAuth or a dictionary with the auth parameters.")
        if auth_action:
            self.auth_module = auth_action
        self.register_urls()

    def register_urls(self):
        pass

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
        request_data_type: DataTypeChoice = None,
        url_params: List[Dict] = [],
        query_params: List[Dict] = [],
        data_params: list = [],
        response_data_type: DataTypeChoice = None,
        response_manager: RESTpyResponse = None,
    ):
        url_params = self._base_url_params + url_params
        if not url or not isinstance(url, str):
            raise ValueError("url is required with type str.")
        if not request_methods or not isinstance(request_methods, List):
            raise ValueError("request_methods is required with type List[HTTPMethod]")
        if not request_data_type:
            request_data_type = self.default_request_data_type
        if not isinstance(request_data_type, str):
            raise ValueError("request_data_type must be an instance of DataTypeChoice.")
        if not all([isinstance(method, HTTPMethod) for method in request_methods]):
            raise ValueError("request_methods must be a list of HTTPMethod instances.")
        if not all([isinstance(param, dict) for param in url_params]):
            raise ValueError("url_params must be a list of dictionaries.")
        if not all([isinstance(param, dict) for param in query_params]):
            raise ValueError("query_params must be a list of dictionaries.")
        if not all([isinstance(param, dict) for param in data_params]):
            raise ValueError("data_params must be a list of dictionaries.")
        if not response_data_type:
            response_data_type = self.default_response_data_type
        if not isinstance(response_data_type, str):
            raise ValueError("response_data_type must be an instance of DataTypeChoice.")
        if response_manager is None:
            response_manager = self.default_response_manager
        if type(response_manager) is RESTpyResponse:
            raise ValueError("response_manager must be an RESTpyResponse class.")
        if name in self.registered_urls:
            raise ValueError(f"Name {name} is already registered in {self.name}.")
        rp_url = RestPyURL(
            name=name,
            url=url,
            request_methods=request_methods,
            request_data_type=request_data_type,
            url_params=url_params,
            query_params=query_params,
            data_params=data_params,
            response_data_type=response_data_type,
            response_manager=response_manager,
        )
        self.registered_urls[name] = rp_url
        self.__registered_urls_list.append(rp_url)

    def search_url(self, *, name: str = None, url_str: str = None):
        if name:
            url = self._search_url_by_name(name)
        elif url_str:
            url = self._search_url_by_url(url_str)
        else:
            raise ValueError("name or url_str is required.")
        if not url:
            self.logger.debug(f"[{self.name}] RestPyURL not found. Params: Name {name} - URL: {url} ")
        return url

    def _search_url_by_name(self, name: str):
        return self.registered_urls.get(name, None)

    def _search_url_by_url(self, url: str):
        return next((rp_url for rp_url in self.registered_urls if rp_url.url == url), None)

    # [Actions]
    def get(self, name: str = None, url_str: str = None, url_params={}, query_params={}, data_params={}, **xtra_params):
        return self._emit_request(
            HTTPMethod.GET, name=name, url_str=url_str, url_params=url_params, query_params=query_params, data_params=data_params, **xtra_params
        )

    def post(self, name: str = None, url_params={}, query_params={}, data_params={}, **xtra_params):
        return self._emit_request(
            HTTPMethod.POST, name=name, url_params=url_params, query_params=query_params, data_params=data_params, **xtra_params
        )

    def put(self, name: str = None, url_params={}, query_params={}, data_params={}, **xtra_params):
        return self._emit_request(HTTPMethod.PUT, name=name, url_params=url_params, query_params=query_params, data_params=data_params, **xtra_params)

    def patch(self, name: str = None, url_params={}, query_params={}, data_params={}, **xtra_params):
        return self._emit_request(
            HTTPMethod.PATCH, name=name, url_params=url_params, query_params=query_params, data_params=data_params, **xtra_params
        )

    def delete(self, name: str = None, url_params={}, query_params={}, data_params={}, **xtra_params):
        return self._emit_request(
            HTTPMethod.DELETE, name=name, url_params=url_params, query_params=query_params, data_params=data_params, **xtra_params
        )

    def _emit_request(self, request_method: HTTPMethod, name: str, url_str: str, url_params, query_params, data_params, **xtra_params):
        rp_url: RestPyURL | None = self.search_url(name=name, url_str=url_str)
        # Validar request method
        field_errors = self._validate_request_method(request_method, rp_url)
        # TODO: Validar la peticion
        if field_errors:
            self.logger.error(f"[{self.name}] Error in request - {field_errors}")
            return self._prepare_response(rp_url, None, field_errors)

        status = self.login()
        response, counter_request, is_refreshed = None, 0, False
        while counter_request < self.RETRIES_URL:
            response = self._send_request(request_method, rp_url, response, url_params, query_params, data_params, **xtra_params)
            counter_request += 1
            if self._check_login_action(response) and not is_refreshed:
                self.logger.info(f"[{self.name}] Login refreshed")
                is_refreshed, status = True, self.login(refresh=True)
                self.logger.debug(f"[{self.name}] Retried login - Result: {status}")
                continue
            if self._check_retry_action_and_timeout(response):
                time.sleep(self.RETRIES_TIMEOUT_SECONDS)
            elif not self._check_retry_action(response):
                break
            self.logger.debug(f"[{self.name}] Retry {counter_request} - {response.status_code}")
        # Validamos status
        field_errors = self._validate_response_status(rp_url, response)
        if field_errors:
            return self._prepare_response(rp_url, response, field_errors)
        # Validamos la response
        field_errors = self.validate_response_data(rp_url, response)
        if field_errors:
            return self._prepare_response(rp_url, response, field_errors)
        return self._prepare_response(rp_url, response, None)

    def _send_request(self, request_method, rp_url, response, url_params, query_params, data_params):
        # Prepare request data
        nheaders, ndata = DataTypeChoice.parse_request(rp_url.request_data_type, data_params)

        # Apply headers
        headers = self.headers.copy()
        headers.update(self.auth_headers)
        headers.update(nheaders)
        if response is None:
            if self.base_url:
                nurl = f"{self.base_url}{rp_url.url}"
            else:
                nurl = rp_url.url
            # Add custom data to pre url
            nurl, nparams = self._apply_custom_data_to_pre_url(request_method, rp_url, nurl, url_params)
            # URI Params
            nurl, nparams = self._generate_url_params_url(request_method, rp_url, nurl, nparams)
            # Add custom data to post url
            nurl, nparams = self._apply_custom_data_to_post_url(request_method, rp_url, nurl, nparams)

            self.logger.debug(f"[{self.name}] {request_method} {nurl} {nparams} {ndata}")
            return RequestMethodChoice.request(request_method)(
                nurl, params=query_params, data=ndata, headers=headers, cookies=self.auth_module.cookies
            )
        else:
            return RequestMethodChoice.request(request_method)(
                response.request.url, params={}, data=ndata, headers=headers, cookies=self.auth_module.cookies
            )

    def _apply_custom_data_to_pre_url(self, request_method, rp_url, nurl, params):
        return nurl, params

    def _apply_custom_data_to_post_url(self, request_method, rp_url, url, params):
        return url, params

    def _generate_url_params_url(self, request_method, rp_url, url, url_params):
        uri_params_url = {}
        for str_field, field in rp_url.url_fields.items():
            url_value = url_params.get(str_field)
            if url_value:
                uri_params_url[str_field] = url_value
                url_params.pop(str_field, None)
        if uri_params_url:
            url = url.format(**uri_params_url)
        return url, url_params

    def _check_login_action(self, response):
        return response.status_code in self.REFRESH_LOGIN_STATUS_CODES

    def _check_retry_action(self, response):
        return response.status_code in self.RETRIES_STATUS_CODES

    def _check_retry_action_and_timeout(self, response):
        return response.status_code in self.RETRIES_TIMEOUT_STATUS_CODES

    def _prepare_response(self, rp_url, response, field_errors):
        if field_errors:
            return rp_url.response_manager(response, None, field_errors)
        return rp_url.response_manager(response, DataTypeChoice.parse_response(rp_url.response_data_type, response), None)

    # [Validators]
    def _validate_request_method(self, request_method, url):
        if url is None:
            return [RestPyURLNotFoundException(url)]
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

    def _validate_request_fields(self, rp_url, url_params, query_params, **xtra_params):
        field_errors = []
        for field_name, rp_field in rp_url.url_fields:
            value, exception = RequiredFieldValidator.validate(rp_field, url_params)
            if exception:
                field_errors.append(exception)
                continue

    def _validate_response_status(self, rp_url, response, **xtra_params):
        list_exceptions = []
        exception = RestPyIsValidStatusResponse.validate(response, valid_status=self._VALID_STATUS)
        if exception:
            for exception in self._validator_runner(self._EXCEPTION_VALID_STATUS_RUNNER, response):
                if exception:
                    list_exceptions.append(exception)
                    break
            return list_exceptions
        if all([rp_url.response_data_type == DataTypeChoice.JSON, not response.text.startswith("{")]):
            response.status_code = HTTPStatus.NO_CONTENT
            self.logger.debug(f"[{self.name}] WARNING STATUS {response.status_code} - NO CONTENT")
        return list_exceptions

    def validate_response_data(self, rp_url, response, **xtra_params):
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
