# Exceptions

## Hierarchy

```
Exception
└── RestPyException                  # library base
    ├── RestPyAuthException          # authentication errors
    ├── RestPyValidatorException     # field validation errors
    ├── RestPyURLNotFoundException   # endpoint not registered
    ├── RestPyResponseTypeException  # unsupported response type
    └── RestPyRunnerException        # exception + validator
        ├── RestPyRequestMethodException
        └── RestPyStatusCodeException
            ├── RestPyIsValidStatusResponse
            ├── RestPyIsInformationalResponse   # 1xx
            ├── RestPyIsSuccessResponse         # 2xx
            ├── RestPyIsRedirectResponse        # 3xx
            ├── RestPyIsClientErrorResponse     # 4xx
            ├── RestPyIsServerErrorResponse     # 5xx
            ├── RestPyLoginException            # 401
            ├── RestPyForbiddenException        # 403
            ├── RestPyMethodNotAllowedException # 405
            ├── RESTpyTimeOutException          # 408
            └── RestPyInternalServerErrorException # 500
```

## `RestPyException`

The base of the whole library.

- `base_message` — fixed text describing the error family.
- `name` (property) — the class name.
- `message` (property) — `"[RESTpy] Exception:{base_message} | {detail}"`.
- `__repr__()` returns `message`.

## `RestPyRunnerException` — exceptions as validators

The library's central pattern: an exception that also knows whether it should exist.
Rather than being raised, it is **returned**.

```python
@classmethod
def validate(cls, response, raise_exception=False, **xtra_params) -> Exception | None
```

- `_validation(response, **xtra_params)` → `bool`: implement it in each subclass; `True`
  means "there is an error".
- `validate()` builds the exception when `_validation()` is true and returns it; with
  `raise_exception=True` it also raises it.

Writing your own runner:

```python
from restpy.exceptions.base import RestPyRunnerException


class ApiBusinessErrorException(RestPyRunnerException):
    base_message = "The API returned a business error"

    @classmethod
    def _validation(cls, response, **xtra_params):
        return response.json().get("status") == "error"


api.add_exception_valid_response_runner(ApiBusinessErrorException())
```

## `RestPyStatusCodeException`

Adds to `RestPyException`:

- `status_code: List[HTTPStatus]` — the codes it stands for.
- `status_description` (property) — the code's description, or
  `"Undefined status description"`.
- `message` (property) — includes the code and its description.
- `_validation()` by default: an error exists when the status is **not** in
  `status_code`.

## Where they show up

| Exception | When |
|---|---|
| `RestPyAuthException` | A request is made with no `auth_module` set; or `RestPyAuthOAuth2` without `oauth_filepath`. **Raised.** |
| `RestPyLoginException` | Login with `refresh=True` fails. **Raised.** |
| `RestPyURLNotFoundException` | The name or path does not match a registered endpoint. **Returned** in `errors`. |
| `RestPyRequestMethodException` | The verb is not in the endpoint's `request_methods`. **Returned** in `errors`. |
| `RestPyIsSuccessResponse` | The default runner when the status is invalid. **Returned** in `errors`. |
| `RestPyResponseTypeException` | Unsupported `response_data_type` at parse time. **Raised.** |
| `RestPyValidatorException` | A field validator rejects a value. **Returned** by `validate()`. |

## What the library uses, and what it offers you

The library itself only builds `RestPyIsSuccessResponse`, `RestPyIsValidStatusResponse`,
`RestPyRequestMethodException`, `RestPyURLNotFoundException`, `RestPyLoginException`,
`RESTpyTimeOutException`, `RestPyAuthException`, `RestPyResponseTypeException` and
`RestPyValidatorException`.

The rest — `RestPyIsInformationalResponse`, `RestPyIsRedirectResponse`,
`RestPyIsClientErrorResponse`, `RestPyIsServerErrorResponse`, `RestPyForbiddenException`,
`RestPyMethodNotAllowedException`, `RestPyInternalServerErrorException` — are **building
blocks for your own runners**: register them with
`add_exception_valid_status_runner()` / `add_exception_valid_response_runner()`.

Every exception is importable from the package root:

```python
from restpy import RestPyIsServerErrorResponse
```

## Recommended handling

```python
response = api.get("users")

if response.errors:
    for error in response.errors:
        logger.error(error.message)
else:
    process(response.data)
```

Configuration errors (missing auth, invalid registration, unrecoverable login) *are*
raised, and are worth wrapping:

```python
from restpy.exceptions.base import RestPyException

try:
    api = MyAPI(base_url="https://api.example.com")
except RestPyException as exc:
    logger.critical(exc.message)
```
