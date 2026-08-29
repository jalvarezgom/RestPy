# API reference

## Public exports

```python
from restpy import RestPy, RestPySingleton, RESTpyResponse, RestPyURL
```

Everything else is imported from its own module:

```python
from restpy.auth.auth import RestPyAuthModule
from restpy.auth.basic import RestPyAuthBasic
from restpy.auth.raw_token import RestPyAuthRawToken
from restpy.auth.oauth2 import RestPyAuthOAuth2
from restpy.auth.disabled import RestPyAuthDisabled
from restpy.choices.data_type import DataTypeChoice
from restpy.choices.request_method import RequestMethodChoice
from restpy.classes.url import RESTpyField, RestPyFieldWhereData
from restpy.validators.base import BaseValidator, ChoiceValidator, DatetimeValidator, IgnoreCaseValidator
from restpy.validators.date import DateYearMonthValidator, DateYearMonthDayValidator, DatetimeObjectValidator
from restpy.validators.number import NumberValidator
from restpy.validators.str import StrValidator
from restpy.validators.required_field import RequiredFieldValidator
from restpy.exceptions.base import RestPyException, RestPyRunnerException
```

## `RestPy` / `RestPySingleton`

Both inherit from `RestPyModule`; `RestPySingleton` additionally mixes in
`SingletonClass`.

```python
RestPy(headers=None, base_url=None, base_url_params=None, auth_action=None)
```

## `RestPyModule`

### Class attributes

| Attribute | Default |
|---|---|
| `auth_module` | `None` |
| `headers` | `{}` |
| `_base_url` | `None` |
| `_base_url_params` | `[]` |
| `RETRIES_URL` | `3` |
| `RETRIES_TIMEOUT_SECONDS` | `1` |
| `RETRIES_TIMEOUT_STATUS_CODES` | `[408, 504]` |
| `RETRIES_STATUS_CODES` | `[408, 504]` |
| `REFRESH_LOGIN_STATUS_CODES` | `[401, 403]` |
| `default_request_data_type` | `DataTypeChoice.DICT` |
| `default_response_data_type` | `DataTypeChoice.JSON` |
| `default_response_manager` | `RESTpyResponse` |
| `_VALID_STATUS` | `[200, 201, 204, 205]` |
| `_EXCEPTION_VALID_STATUS_RUNNER` | `[RestPyIsSuccessResponse]` |
| `_EXCEPTION_VALID_RESPONSE_RUNNER` | `[]` |

### Properties

| Property | Description |
|---|---|
| `name` | The client class's name. |
| `base_url` | Current base URL. |
| `auth_headers` | Headers produced by the auth module. |
| `logger` | The `restpy` logger (or the root logger when that one has no handlers). |
| `registered_urls` | `Dict[str, RestPyURL]` of registered endpoints. |
| `session` | The client's `requests.Session`, created on first use. Connections to the host are pooled and reused. |

### Methods

| Method | Description |
|---|---|
| `register_urls()` | Empty hook invoked at the end of `__init__`. Override it to declare endpoints. |
| `register(...)` | Registers an endpoint. See [URLs and fields](urls-and-fields.md). |
| `set_base_url(base_url)` | Changes the base URL. |
| `close()` | Closes the session and releases the pooled connections. The client stays usable: the next request opens a new session. Also available as a context manager (`with MyAPI(...) as api:`). |
| `set_auth(auth_action)` | Sets the authentication module. `ValueError` if it is not a `RestPyAuthModule`. |
| `login(refresh=False)` | Authenticates. `RestPyAuthException` when there is no auth module. |
| `search_url(*, name=None, url_str=None)` | Looks an endpoint up. `ValueError` when no criterion is given. |
| `get / post / put / patch / delete` | Emit the request and return a `RESTpyResponse`. |
| `add_valid_status(code)` / `remove_valid_status(code)` | Manage `_VALID_STATUS`. Require an `HTTPStatus`. |
| `add_exception_valid_status_runner(r)` / `remove_...` | Manage `_EXCEPTION_VALID_STATUS_RUNNER`. |
| `add_exception_valid_response_runner(r)` / `remove_...` | Manage `_EXCEPTION_VALID_RESPONSE_RUNNER`. |
| `validate_response_data(rp_url, response)` | Runs the payload runners. Overridable. |

### Overridable protected methods

| Method | Description |
|---|---|
| `_apply_custom_data_to_pre_url(request_method, rp_url, nurl, params)` | Adjusts URL/params before path parameter substitution. Returns `(url, params)`. |
| `_apply_custom_data_to_post_url(request_method, rp_url, url, params)` | Same, after substitution. |
| `_check_login_action(response)` | Should the login be refreshed? |
| `_check_retry_action(response)` | Should the request be retried? |
| `_check_retry_action_and_timeout(response)` | Should the retry wait first? |
| `_prepare_response(rp_url, response, field_errors)` | Builds the final response object. |
| `_validate_request_method(request_method, url)` | Validates the verb against the endpoint. |
| `_validate_response_status(rp_url, response)` | Validates the status code. |

## `RestPyURL`

```python
RestPyURL(name=None, url="", request_methods=ALL_REQUEST_METHODS, request_data_type=None,
          url_params=[], query_params=[], data_params=[], response_data_type=None,
          response_manager=None)
```

`ALL_REQUEST_METHODS = [GET, POST, PUT, PATCH, DELETE]`.

Members: `name`, `url`, `request_methods`, `request_data_type`, `response_data_type`,
`response_manager`, `fields_list`, `url_fields`, `query_fields`, `data_fields`,
`get_field(name)`.

## `RESTpyField`

```python
RESTpyField(*, where_data: RestPyFieldWhereData, name: str, is_required=False, validator=None, **xtra_params)
```

Members: `where_data`, `name`, `required`, `validator`.

## `RESTpyResponse`

```python
RESTpyResponse(response, data=None, errors=None)
```

Properties: `data`, `url`, `response`, `status_code`; attribute `errors`.
Overridable: `_parse_data(data)`.

## `DataTypeChoice`

Constants `JSON`, `XML`, `TEXT`, `DICT`. Static methods `parse_request(type, data)`,
`parse_response(type, response)`, `get_token(response, get_token_method, get_token_key)`.

## `RequestMethodChoice`

`RequestMethodChoice.request(HTTPMethod.GET, session=None)` returns the matching verb:
bound to `session` when one is given, otherwise the module-level `requests` function.
Supports `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD` and `OPTIONS`.

## Utilities

| Item | Module | Description |
|---|---|---|
| `SingletonMeta` | `utils/singleton_meta.py` | `__new__` that always reuses the same instance. |
| `SingletonClass` | `utils/singleton_meta.py` | Adds `_is_init` so `__init__` runs only once. |
| `classproperty` | `utils/classproperty.py` | Property decorator accessible from the class. |
