# Architecture

## Package layout

```
restpy/
├── __init__.py          # Public API: RestPy, RestPySingleton, RESTpyResponse, RestPyURL
├── classes/
│   ├── module.py        # RestPyModule — the engine: registration, verbs, retries, validation
│   ├── restpy.py        # RestPy and RestPySingleton (facades over RestPyModule)
│   ├── url.py           # RestPyURL, RESTpyField, RestPyFieldWhereData
│   └── response.py      # RESTpyResponse
├── auth/
│   ├── auth.py          # RestPyAuthModule (base class)
│   ├── basic.py         # RestPyAuthBasic — username/password login → token
│   ├── raw_token.py     # RestPyAuthRawToken — fixed token, no login
│   ├── oauth2.py        # RestPyAuthOAuth2 — file-backed token + refresh_token
│   └── disabled.py      # RestPyAuthDisabled — no authentication
├── choices/
│   ├── data_type.py     # DataTypeChoice — JSON, XML, TEXT, DICT serialization/parsing
│   └── request_method.py# RequestMethodChoice — HTTPMethod → verb, bound to the client's Session
├── validators/
│   ├── base.py          # BaseValidator, ChoiceValidator, DatetimeValidator, IgnoreCaseValidator
│   ├── date.py          # Preconfigured date validators
│   ├── number.py        # NumberValidator
│   ├── str.py           # StrValidator
│   └── required_field.py# RequiredFieldValidator
├── exceptions/
│   ├── base.py          # RestPyException, RestPyRunnerException
│   ├── auth.py          # RestPyAuthException
│   ├── request.py       # RestPyURLNotFoundException, RestPyRequestMethodException, ...
│   ├── status_codes.py  # HTTP status/range exception family
│   └── validators.py    # RestPyValidatorException
└── utils/
    ├── singleton_meta.py# SingletonMeta, SingletonClass
    └── classproperty.py # classproperty decorator
```

## Building blocks

| Piece | Responsibility |
|---|---|
| `RestPyModule` | The core engine. Holds `base_url`, headers, the auth module and the URL registry. Exposes `get/post/put/patch/delete`. |
| `RestPyURL` | A registered endpoint: name, URL template, allowed methods, data types and fields. |
| `RESTpyField` | A single endpoint parameter, with its location (`URI`, `QUERY`, `BODY`), whether it is required, and its validator. |
| `RestPyAuthModule` | Authentication strategy: performs `login()`, stores the token and builds the authorization headers. |
| `DataTypeChoice` | Converts the request body and parses the response body according to the declared type. |
| `RESTpyResponse` | Result wrapper: the raw `requests` response, the parsed data and the error list. |
| `RestPyRunnerException` | An exception that is also a *validator*: its `validate()` returns the exception instead of raising it. |

## Request lifecycle

`RestPyModule._emit_request()` is the single funnel every verb goes through:

1. **Endpoint resolution** — `search_url()` looks the `RestPyURL` up by name (or by URL).
   If it doesn't exist, a `RESTpyResponse` carrying `RestPyURLNotFoundException` is
   returned.
2. **Method validation** — `RestPyRequestMethodException` checks the verb is listed in the
   endpoint's `request_methods`. On failure it short-circuits and returns the error.
3. **Login** — `login()` authenticates if there is no token yet, and builds the auth
   headers.
4. **Send loop** (up to `RETRIES_URL` attempts, 3 by default):
   - `_send_request()` builds the URL and headers and performs the call via `requests`.
   - If the status is in `REFRESH_LOGIN_STATUS_CODES` (401, 403) and no refresh has
     happened yet, `login(refresh=True)` runs **once** and the request is retried.
   - If the status is in `RETRIES_TIMEOUT_STATUS_CODES` (408, 504), it waits
     `RETRIES_TIMEOUT_SECONDS` and retries.
   - If no retry applies, the loop exits.
5. **Status validation** — `_validate_response_status()` checks the code against
   `_VALID_STATUS`; if it doesn't match, the `_EXCEPTION_VALID_STATUS_RUNNER` runners fire.
6. **Payload validation** — `validate_response_data()` runs the
   `_EXCEPTION_VALID_RESPONSE_RUNNER` runners.
7. **Response construction** — `_prepare_response()` parses the body via
   `DataTypeChoice.parse_response()` and returns the endpoint's `response_manager`
   (`RESTpyResponse` by default).

Important: **errors are not raised**. They come back inside `RESTpyResponse.errors` as a
list of exceptions, so the caller decides what to do.

## Extension points

- `register_urls()` — declare the class's endpoints.
- `_apply_custom_data_to_pre_url()` / `_apply_custom_data_to_post_url()` — inject data
  into the URL before and after path parameter substitution (empty hooks by default).
- `_check_login_action()` / `_check_retry_action()` / `_check_retry_action_and_timeout()` —
  redefine when to refresh the login or retry.
- `default_response_manager`, or the `response_manager` argument of `register()` — use a
  `RESTpyResponse` subclass with your own parsing logic.
- `add_valid_status()` / `remove_valid_status()` — adjust which codes count as valid.
- `add_exception_valid_status_runner()` / `add_exception_valid_response_runner()` — add
  status or payload validations to the response.
