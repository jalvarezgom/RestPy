import logging
import string
import time
from http import HTTPStatus, HTTPMethod
from logging import Logger
from typing import List, Dict

import requests

from restpy.classes.url import RestPyURL, RestPyFieldWhereData
from restpy.auth.auth import RestPyAuthModule
from restpy.choices.data_type import DataTypeChoice
from restpy.classes.response import RESTpyResponse
from restpy.exceptions.auth import RestPyAuthException
from restpy.exceptions.base import RestPyRunnerException
from restpy.exceptions.request import RestPyConnectionException, RestPyRequestMethodException, RestPyURLNotFoundException, RestPyURLParamsException
from restpy.exceptions.status_codes import (
    RestPyLoginException,
    RestPyIsSuccessResponse,
    RestPyIsValidStatusResponse,
    RESTpyTimeOutException,
)
from restpy.choices.request_method import RequestMethodChoice
from restpy.validators.required_field import RequiredFieldValidator


class _KeepPlaceholders(dict):
    """`str.format_map` mapping that leaves unknown placeholders untouched."""

    def __missing__(self, key):
        return "{" + key + "}"


class RestPyModule:
    """Client for one REST API: a registry of endpoints plus the machinery to call them.

    Subclass it and override `register_urls()` (or call `register()` on an instance) to declare
    the endpoints, then call them by name with `get`, `post`, `put`, `patch` and `delete`.
    Every call returns a `RESTpyResponse`; failures (validation, login, network, status) are
    reported in `response.errors` instead of being raised.

    The class attributes below are declarative defaults. Mutable ones (`headers`, the valid
    status list and the runners) are copied per instance in `__init__`, so changing one client
    never affects another.

    Retry settings:
        RETRIES_URL: maximum attempts per request. A login refresh does not consume one.
        RETRIES_TIMEOUT_SECONDS: pause between attempts.
        REQUEST_TIMEOUT_SECONDS: timeout passed to every network call.

    Connection settings:
        ssl_verify: passed as `verify` to every `requests` call (True by default). Accepts a bool
            or the path to a CA bundle. The auth module's own calls use its own `ssl_verify` instead.
        RETRIES_TIMEOUT_STATUS_CODES: statuses that are retried after a pause.
        RETRIES_STATUS_CODES: statuses that are retried.
        REFRESH_LOGIN_STATUS_CODES: statuses that trigger one login refresh (401 by default).
    """

    # [AUTH]
    auth_module: RestPyAuthModule = None

    # [Actions]
    RETRIES_URL = 3
    RETRIES_TIMEOUT_SECONDS = 1
    REQUEST_TIMEOUT_SECONDS = 30
    ssl_verify = True
    RETRIES_TIMEOUT_STATUS_CODES = [HTTPStatus.REQUEST_TIMEOUT, HTTPStatus.GATEWAY_TIMEOUT]
    RETRIES_STATUS_CODES = [HTTPStatus.REQUEST_TIMEOUT, HTTPStatus.GATEWAY_TIMEOUT]
    REFRESH_LOGIN_STATUS_CODES = [HTTPStatus.UNAUTHORIZED]
    _base_url: str = None
    _base_url_params: list = []

    # TODO: extract into its own entity
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
    _session: requests.Session = None

    def __init__(self, headers: dict = None, base_url: str = None, base_url_params: list = None, auth_action: RestPyAuthModule = None, ssl_verify: bool = None):
        """Create a client.

        Args:
            headers: Headers sent on every request. They replace the class-level `headers`.
            base_url: Prefix prepended to every registered endpoint URL.
            base_url_params: Field definitions (`url_params` dicts) added to every endpoint, for
                placeholders that live in the base URL.
            auth_action: Authentication module. It can also be set later with `set_auth()`.
            ssl_verify: Verify TLS certificates (bool or CA bundle path). Defaults to the class
                attribute, which is True.

        Raises:
            ValueError: If `auth_action` is not a `RestPyAuthModule` instance.
        """
        self.registered_urls: Dict[str, RestPyURL] = {}
        self._registrations: Dict[str, dict] = {}
        self._session: requests.Session = None
        self.headers = dict(self.headers)
        self._base_url_params = list(self._base_url_params)
        self._VALID_STATUS = list(self._VALID_STATUS)
        self._EXCEPTION_VALID_STATUS_RUNNER = list(self._EXCEPTION_VALID_STATUS_RUNNER)
        self._EXCEPTION_VALID_RESPONSE_RUNNER = list(self._EXCEPTION_VALID_RESPONSE_RUNNER)
        if headers:
            self.headers = dict(headers)
        if ssl_verify is not None:
            self.ssl_verify = ssl_verify
        if base_url:
            self._base_url = base_url
        if base_url_params:
            self._base_url_params = list(base_url_params)
        if auth_action and not (isinstance(auth_action, RestPyAuthModule)):
            raise ValueError("auth_action must be an instance of RestPyAuth or a dictionary with the auth parameters.")
        if auth_action:
            self.auth_module = auth_action
        self.register_urls()

    def register_urls(self):
        """Hook called at the end of `__init__`. Override it to call `register()` for each endpoint."""

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
    def session(self) -> requests.Session:
        """Per-client `requests.Session`, so connections to the host are pooled and reused."""
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def close(self):
        """Release the pooled connections. The client stays usable: a new session is created on demand."""
        if self._session is not None:
            self._session.close()
            self._session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @property
    def logger(self):
        """The `restpy` logger, or the root logger when `restpy` has no handlers configured."""
        if not self._logger:
            self._logger = logging.getLogger("restpy")
            if not self._logger.hasHandlers():
                self._logger = logging.getLogger()
        return self._logger

    # [Authentication]
    def set_auth(self, auth_action):
        """Replace the authentication module. Raises `ValueError` if it is not a `RestPyAuthModule`."""
        if not isinstance(auth_action, RestPyAuthModule):
            raise ValueError("auth_action must be an instance of RestPyAuth")
        self.auth_module = auth_action

    def login(self, refresh=False):
        """Authenticate and build the auth headers.

        The auth module is only asked to log in when `refresh` is true or it has no token yet.

        Args:
            refresh: Force a new login (used after a 401).

        Returns:
            True on success. False when the first login fails.

        Raises:
            RestPyAuthException: If no auth module is configured.
            RestPyLoginException: If a forced refresh fails.
        """
        if not self.auth_module:
            raise RestPyAuthException('You must define "auth_module" variable with a valid RESTpyAuth class.')
        status = True
        if refresh or not self.auth_module.token:
            status = self.auth_module.login(refresh=refresh)
            if not status and refresh:
                raise RestPyLoginException(self.name)
            if not status:
                self.logger.error(f"{RestPyLoginException(self.name)} | Login failed, a refresh is needed ")
                return status
        self.auth_module.generate_auth_headers()
        return status

    # [API]
    def set_base_url(self, base_url: str, base_url_params: List[Dict] = None):
        """Change the base URL and, optionally, its placeholders.

        The new `base_url_params` replace the previous ones on every endpoint that is
        already registered, so calling this after `register()` is safe.
        """
        self._base_url = base_url
        if base_url_params is not None:
            self._base_url_params = list(base_url_params)
            self._rebuild_registered_urls()

    def _rebuild_registered_urls(self):
        """Re-create every endpoint from its original registration, with the current base params."""
        registrations = self._registrations
        self.registered_urls, self._registrations = {}, {}
        for registration in registrations.values():
            self.register(**registration)

    def register(
        self,
        name: str = None,
        url: str = None,
        request_methods: List[HTTPMethod] = None,
        request_data_type: DataTypeChoice = None,
        url_params: List[Dict] = None,
        query_params: List[Dict] = None,
        data_params: list = None,
        response_data_type: DataTypeChoice = None,
        response_manager: RESTpyResponse = None,
    ):
        """Declare an endpoint so it can be called by name.

        Args:
            name: Unique name of the endpoint in this client.
            url: Path appended to the base URL. Use `{field}` placeholders for URL params.
            request_methods: HTTP methods the endpoint accepts. Other verbs are rejected.
            request_data_type: How the body is sent. Defaults to `default_request_data_type`.
            url_params: Field definitions for the placeholders in `url`.
            query_params: Field definitions for the query string.
            data_params: Field definitions for the body.
            response_data_type: How the response is parsed. Defaults to `default_response_data_type`.
            response_manager: `RESTpyResponse` subclass used to wrap the response.

        Each field definition is a dict accepted by `RESTpyField` (`name`, `is_required`,
        `allow_empty`, `validator`). The base URL params are added to `url_params`.

        Raises:
            ValueError: If an argument is invalid or `name` is already registered.
        """
        registration = {
            "name": name,
            "url": url,
            "request_methods": request_methods,
            "request_data_type": request_data_type,
            "url_params": url_params,
            "query_params": query_params,
            "data_params": data_params,
            "response_data_type": response_data_type,
            "response_manager": response_manager,
        }
        url_params = self._base_url_params + list(url_params or [])
        query_params, data_params = list(query_params or []), list(data_params or [])
        if not url or not isinstance(url, str):
            raise ValueError("url is required with type str.")
        if not request_methods or not isinstance(request_methods, List):
            raise ValueError("request_methods is required with type List[HTTPMethod]")
        if not request_data_type:
            request_data_type = self.default_request_data_type
        request_data_type = self._validate_data_type(request_data_type, "request_data_type")
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
        response_data_type = self._validate_data_type(response_data_type, "response_data_type")
        if response_data_type == DataTypeChoice.DICT:
            raise ValueError("response_data_type cannot be DataTypeChoice.DICT: it only describes how a request body is sent.")
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
        self._registrations[name] = registration

    @staticmethod
    def _validate_data_type(data_type, argument_name):
        try:
            return DataTypeChoice(data_type)
        except ValueError:
            raise ValueError(f"{argument_name} must be a DataTypeChoice member, got {data_type!r}.") from None

    def search_url(self, *, name: str = None, url_str: str = None):
        """Find a registered endpoint by `name`, or by its `url` path when no name is given.

        Returns:
            The `RestPyURL`, or None when nothing matches.

        Raises:
            ValueError: If neither `name` nor `url_str` is given.
        """
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
        return next((rp_url for rp_url in self.registered_urls.values() if rp_url.url == url), None)

    # [Actions]
    # `get`, `post`, `put`, `patch` and `delete` share one signature:
    #   name / url_str: the endpoint, by registered name or by its URL path.
    #   url_params / query_params / data_params: values for the declared fields; the dicts are not modified.
    #   **xtra_params: forwarded to the `_apply_custom_data_to_*_url` hooks and to field validation.
    # They return a `RESTpyResponse` and do not raise on request failures.
    def get(self, name: str = None, url_str: str = None, url_params: dict = None, query_params: dict = None, data_params: dict = None, **xtra_params):
        return self._emit_request(
            HTTPMethod.GET, name=name, url_str=url_str, url_params=url_params, query_params=query_params, data_params=data_params, **xtra_params
        )

    def post(
        self, name: str = None, url_str: str = None, url_params: dict = None, query_params: dict = None, data_params: dict = None, **xtra_params
    ):
        return self._emit_request(
            HTTPMethod.POST, name=name, url_str=url_str, url_params=url_params, query_params=query_params, data_params=data_params, **xtra_params
        )

    def put(self, name: str = None, url_str: str = None, url_params: dict = None, query_params: dict = None, data_params: dict = None, **xtra_params):
        return self._emit_request(
            HTTPMethod.PUT, name=name, url_str=url_str, url_params=url_params, query_params=query_params, data_params=data_params, **xtra_params
        )

    def patch(
        self, name: str = None, url_str: str = None, url_params: dict = None, query_params: dict = None, data_params: dict = None, **xtra_params
    ):
        return self._emit_request(
            HTTPMethod.PATCH, name=name, url_str=url_str, url_params=url_params, query_params=query_params, data_params=data_params, **xtra_params
        )

    def delete(
        self, name: str = None, url_str: str = None, url_params: dict = None, query_params: dict = None, data_params: dict = None, **xtra_params
    ):
        return self._emit_request(
            HTTPMethod.DELETE, name=name, url_str=url_str, url_params=url_params, query_params=query_params, data_params=data_params, **xtra_params
        )

    def _emit_request(
        self, request_method: HTTPMethod, name: str = None, url_str: str = None, url_params=None, query_params=None, data_params=None, **xtra_params
    ):
        """Run one request end to end and always return a `RESTpyResponse`.

        Order: resolve the endpoint and check the verb, validate the fields, log in, send with
        retries (timeouts, 408/504, one login refresh on 401), then validate the status and the
        payload. The first failing stage returns a response whose `errors` explains it.
        """
        rp_url: RestPyURL | None = self.search_url(name=name, url_str=url_str)
        # Validate the request method
        field_errors = self._validate_request_method(request_method, rp_url)
        if field_errors:
            self.logger.error(f"[{self.name}] Error in request - {field_errors}")
            return self._prepare_response(rp_url, None, field_errors)
        url_params, query_params, data_params = dict(url_params or {}), dict(query_params or {}), dict(data_params or {})
        field_errors = self._validate_request_fields(rp_url, url_params, query_params, data_params, **xtra_params)
        if field_errors:
            self.logger.error(f"[{self.name}] Error in request fields - {field_errors}")
            return self._prepare_response(rp_url, None, field_errors)

        try:
            status = self.login()
        except requests.RequestException as exc:
            return self._prepare_response(rp_url, None, [self._network_error(exc)])
        if not status:
            return self._prepare_response(rp_url, None, [RestPyLoginException(self.name)])
        response, counter_request, is_refreshed, timeout_exception = None, 0, False, None
        while counter_request < self.RETRIES_URL:
            try:
                response = self._send_request(request_method, rp_url, response, url_params, query_params, data_params, **xtra_params)
                timeout_exception = None
            except requests.Timeout as exc:
                timeout_exception = exc
                response, counter_request = None, counter_request + 1
                self.logger.warning(f"[{self.name}] Timeout {counter_request} after {self.REQUEST_TIMEOUT_SECONDS}s - {exc}")
                if counter_request < self.RETRIES_URL:
                    time.sleep(self.RETRIES_TIMEOUT_SECONDS)
                continue
            except RestPyURLParamsException as exc:
                self.logger.error(f"[{self.name}] Error in URL params - {exc}")
                return self._prepare_response(rp_url, None, [exc])
            except requests.RequestException as exc:
                self.logger.error(f"[{self.name}] Request failed - {exc}")
                return self._prepare_response(rp_url, None, [self._network_error(exc)])
            counter_request += 1
            if self._check_login_action(response) and not is_refreshed:
                self.logger.info(f"[{self.name}] Login refreshed")
                try:
                    is_refreshed, status = True, self.login(refresh=True)
                except RestPyLoginException as exc:
                    return self._prepare_response(rp_url, response, [exc])
                except requests.RequestException as exc:
                    return self._prepare_response(rp_url, response, [self._network_error(exc)])
                self.logger.debug(f"[{self.name}] Retried login - Result: {status}")
                # The refresh only happens once, so giving the attempt back cannot loop forever
                counter_request -= 1
                continue
            if self._check_retry_action_and_timeout(response):
                time.sleep(self.RETRIES_TIMEOUT_SECONDS)
            elif not self._check_retry_action(response):
                break
            self.logger.debug(f"[{self.name}] Retry {counter_request} - {response.status_code}")
        if timeout_exception is not None:
            return self._prepare_response(rp_url, None, [RESTpyTimeOutException(str(timeout_exception))])
        # Validate the response status
        field_errors = self._validate_response_status(rp_url, response)
        if field_errors:
            return self._prepare_response(rp_url, response, field_errors)
        # Validate the response payload
        field_errors = self.validate_response_data(rp_url, response)
        if field_errors:
            return self._prepare_response(rp_url, response, field_errors)
        return self._prepare_response(rp_url, response, None)

    @staticmethod
    def _network_error(exc):
        """Map a `requests` failure to `RESTpyTimeOutException` or `RestPyConnectionException`."""
        if isinstance(exc, requests.Timeout):
            return RESTpyTimeOutException(str(exc))
        return RestPyConnectionException(str(exc))

    def _send_request(self, request_method, rp_url, response, url_params, query_params, data_params, **xtra_params):
        """Send one HTTP request.

        With `response=None` the URL is built from the base URL, the endpoint path, the URL
        params and the two hooks. With a previous `response` (a retry) its final URL is reused.

        Raises:
            RestPyURLParamsException: If a URL param is undeclared or a placeholder is left unresolved.
            requests.RequestException: On network failure; `_emit_request` turns it into an error response.
        """
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
            nurl, nparams = self._apply_custom_data_to_pre_url(request_method, rp_url, nurl, url_params, **xtra_params)
            # URI Params
            nurl, nparams = self._generate_url_params_url(request_method, rp_url, nurl, nparams)
            # Add custom data to post url
            nurl, nparams = self._apply_custom_data_to_post_url(request_method, rp_url, nurl, nparams, **xtra_params)
            unresolved = [name for _, name, _, _ in string.Formatter().parse(nurl) if name]
            if unresolved:
                raise RestPyURLParamsException(f"Unresolved URL placeholders: {', '.join(unresolved)}")

            self.logger.debug(f"[{self.name}] {request_method} {nurl}")
            return RequestMethodChoice.request(request_method, session=self.session)(
                nurl, params=query_params, data=ndata, headers=headers, cookies=self.auth_module.cookies, timeout=self.REQUEST_TIMEOUT_SECONDS, verify=self.ssl_verify
            )
        else:
            return RequestMethodChoice.request(request_method, session=self.session)(
                response.request.url,
                params={},
                data=ndata,
                headers=headers,
                cookies=self.auth_module.cookies,
                timeout=self.REQUEST_TIMEOUT_SECONDS,
                verify=self.ssl_verify,
            )

    def _apply_custom_data_to_pre_url(self, request_method, rp_url, nurl, params, **xtra_params):
        """Hook run before the URL params are substituted. Return the `(url, params)` to continue with."""
        return nurl, params

    def _apply_custom_data_to_post_url(self, request_method, rp_url, url, params, **xtra_params):
        """Hook run after the URL params are substituted. Return the `(url, params)` to continue with."""
        return url, params

    def _generate_url_params_url(self, request_method, rp_url, url, url_params):
        """Substitute the declared URL params into `url`, consuming them from `url_params`.

        Values are inserted as they are, without percent-encoding.

        Raises:
            RestPyURLParamsException: If `url_params` holds keys that are not declared fields.
        """
        uri_params_url = {}
        for str_field in rp_url.url_fields:
            url_value = url_params.pop(str_field, None)
            if url_value is not None:
                uri_params_url[str_field] = url_value
        if url_params:
            raise RestPyURLParamsException(f"Undeclared URL params: {', '.join(map(str, url_params))}")
        if uri_params_url:
            url = url.format_map(_KeepPlaceholders(uri_params_url))
        return url, url_params

    def _check_login_action(self, response):
        return response.status_code in self.REFRESH_LOGIN_STATUS_CODES

    def _check_retry_action(self, response):
        return response.status_code in self.RETRIES_STATUS_CODES

    def _check_retry_action_and_timeout(self, response):
        return response.status_code in self.RETRIES_TIMEOUT_STATUS_CODES

    def _prepare_response(self, rp_url, response, field_errors):
        """Wrap `response` with the endpoint's `response_manager`. With errors, no data is parsed."""
        response_manager = rp_url.response_manager if rp_url is not None else self.default_response_manager
        if field_errors:
            return response_manager(response, None, field_errors)
        return response_manager(response, DataTypeChoice.parse_response(rp_url.response_data_type, response), None)

    # [Validators]
    def _validate_request_method(self, request_method, url):
        """Return the errors for an unknown endpoint or a verb the endpoint does not accept."""
        if url is None:
            return [RestPyURLNotFoundException(url)]
        exception = RestPyRequestMethodException.validate(request_method, url=url)
        if exception:
            return [exception]
        return []

    def _validate_request_fields(self, rp_url, url_params, query_params, data_params, **xtra_params):
        """Check required fields and run each field's validator, for the three locations.

        Validated values replace the originals in the given dicts, so pass copies. Returns the
        list of exceptions found.
        """
        field_errors = []
        params_by_where = {
            RestPyFieldWhereData.URL_PARAMS: url_params,
            RestPyFieldWhereData.QUERY_PARAMS: query_params,
            RestPyFieldWhereData.BODY: data_params,
        }
        for rp_field in rp_url.fields_list:
            params = params_by_where.get(rp_field.where_data)
            if not isinstance(params, dict):
                continue
            _, exception = RequiredFieldValidator.validate(rp_field, params)
            if exception:
                field_errors.append(exception)
                continue
            if not rp_field.validator:
                continue
            value, exception = rp_field.validator.validate(rp_field.name, params.get(rp_field.name, None))
            if exception:
                field_errors.append(exception)
            elif value is not None:
                params[rp_field.name] = value
        return field_errors

    def _validate_response_status(self, rp_url, response, **xtra_params):
        """Return an error only when the status is outside `_VALID_STATUS` and a status runner flags it."""
        list_exceptions = []
        exception = RestPyIsValidStatusResponse.validate(response, valid_status=self._VALID_STATUS)
        if exception:
            for exception in self._validator_runner(self._EXCEPTION_VALID_STATUS_RUNNER, response):
                if exception:
                    list_exceptions.append(exception)
                    break
            return list_exceptions
        if not response.text:
            self.logger.debug(f"[{self.name}] STATUS {response.status_code} - NO CONTENT")
        return list_exceptions

    def validate_response_data(self, rp_url, response, **xtra_params):
        """Run the response runners and return the first error found. Override for custom payload checks."""
        list_exceptions = []
        for exception in self._validator_runner(self._EXCEPTION_VALID_RESPONSE_RUNNER, response):
            if exception:
                list_exceptions.append(exception)
                break
        return list_exceptions

    def add_valid_status(self, status_code):
        """Accept `status_code` (an `HTTPStatus`) as a valid response status for this client."""
        if not isinstance(status_code, HTTPStatus):
            raise ValueError("status_code must be an instance of HTTPStatus")
        self._VALID_STATUS.append(status_code)

    def remove_valid_status(self, status_code):
        """Stop accepting `status_code` (an `HTTPStatus`). Raises `ValueError` if it is not in the list."""
        if not isinstance(status_code, HTTPStatus):
            raise ValueError("status_code must be an instance of HTTPStatus")
        self._VALID_STATUS.remove(status_code)

    @staticmethod
    def _validate_exception_runner(exception_runner):
        # The runners are used as classes: `_validator_runner()` calls `validate()` on them,
        # and the defaults are classes too.
        if not (isinstance(exception_runner, type) and issubclass(exception_runner, RestPyRunnerException)):
            raise ValueError("exception_runner must be a RestPyRunnerException subclass")

    def add_exception_valid_status_runner(self, exception_runner):
        """Add a `RestPyRunnerException` subclass that flags a response status as an error."""
        self._validate_exception_runner(exception_runner)
        self._EXCEPTION_VALID_STATUS_RUNNER.append(exception_runner)

    def remove_exception_valid_status_runner(self, exception_runner):
        """Remove a status runner added with `add_exception_valid_status_runner` (or a default one)."""
        self._validate_exception_runner(exception_runner)
        self._EXCEPTION_VALID_STATUS_RUNNER.remove(exception_runner)

    def add_exception_valid_response_runner(self, exception_runner):
        """Add a `RestPyRunnerException` subclass that flags a response payload as an error."""
        self._validate_exception_runner(exception_runner)
        self._EXCEPTION_VALID_RESPONSE_RUNNER.append(exception_runner)

    def remove_exception_valid_response_runner(self, exception_runner):
        """Remove a response runner added with `add_exception_valid_response_runner`."""
        self._validate_exception_runner(exception_runner)
        self._EXCEPTION_VALID_RESPONSE_RUNNER.remove(exception_runner)

    def _validator_runner(self, validations_to_run, response, **xtra_params):
        """Yield the result of `validate(response)` for each runner: an exception or None."""
        for exception_runner in validations_to_run:
            exception = exception_runner.validate(response)
            yield exception
