# Authentication

Authentication is encapsulated in an **auth module**: a `RestPyAuthModule` subclass that
knows how to obtain a token and turn it into HTTP headers.

It can be attached in three equivalent ways:

```python
# 1. Class attribute
class MyAPI(RestPy):
    auth_module = RestPyAuthRawToken(raw_token="abc")

# 2. Constructor argument
api = MyAPI(auth_action=RestPyAuthRawToken(raw_token="abc"))

# 3. After instantiation
api.set_auth(RestPyAuthRawToken(raw_token="abc"))
```

Without an auth module, the first request raises `RestPyAuthException`. For public APIs,
use `RestPyAuthDisabled`.

## `RestPyAuthModule` (base class)

| Attribute | Default | Description |
|---|---|---|
| `mode` | `None` | Mode label (`"BASIC"`, `"RAW_TOKEN"`, `"OAUTH2"`, `"DISABLED"`). |
| `authorization_key` | `"Authorization"` | Name of the authorization header. |
| `authorization_value_format` | `"Bearer {token}"` | Value template; `{token}` is substituted. |
| `auth_headers` | `None` | Generated headers, merged by `RestPyModule` into every request. |
| `token` (property) | `None` | Current token. |
| `cookies` (property) | `{}` | Cookies sent with every request. |

Any extra `kwarg` passed to the constructor is set as an instance attribute, which is how
`authorization_key` and `authorization_value_format` can be customized inline.

Methods a subclass must implement:

- `login(refresh=False)` → `bool`. Obtains the token. `refresh=True` means the previous
  token was rejected (401/403) and must be renewed.
- `generate_auth_headers(**params)` → `dict`. By default it formats
  `{authorization_key: authorization_value_format.format(token=self.token)}`.

## Built-in modes

### `RestPyAuthRawToken`

A static token known up front. `login()` merely checks that the token is present.

```python
from restpy.auth.raw_token import RestPyAuthRawToken

auth = RestPyAuthRawToken(
    raw_token="RGAPI-xxxx",
    authorization_key="X-Riot-Token",     # optional
    authorization_value_format="{token}", # optional: no "Bearer" prefix
)
```

### `RestPyAuthBasic`

`POST`s to `auth_url` with a username and password, then extracts the token from the
response.

```python
from restpy.auth.basic import RestPyAuthBasic

auth = RestPyAuthBasic(
    auth_url="https://api.example.com/login",
    send_auth_in_body=True,   # True → credentials in the JSON body; False → in query params
    username="user",
    password="secret",
    get_token_method="json",  # response attribute/method to read the token from
    get_token_key="token",    # key inside the JSON
)
```

`get_token_method` is the name of an attribute on the `requests` response. With `"json"`
the library calls `response.json()` and reads `get_token_key`; with `"text"` it takes
`response.text` verbatim. Login is considered successful only on status `200`.

### `RestPyAuthOAuth2`

Stores and reloads the complete OAuth2 token (including the `refresh_token`) in a JSON
file.

```python
from restpy.auth.oauth2 import RestPyAuthOAuth2

auth = RestPyAuthOAuth2(
    client_id="...",
    client_secret="...",
    oauth_filepath="/path/to/oauth_token.json",
    oauth_token_url="https://api.example.com/oauth/token",
)
```

- `login(refresh=False)` loads the token from `oauth_filepath`.
- `login(refresh=True)` `POST`s to `oauth_token_url` with `grant_type=refresh_token`,
  writes the new token back to the file and uses it.
- `generate_auth_headers()` uses `token["access_token"]`.

The file must contain the JSON returned by the OAuth2 provider, with at least
`access_token` and `refresh_token`. If `oauth_filepath` is not set, `RestPyAuthException`
is raised.

### `RestPyAuthDisabled`

No authentication: `login()` returns `True` and `auth_headers` stays empty.

```python
from restpy.auth.disabled import RestPyAuthDisabled

api = MyAPI(auth_action=RestPyAuthDisabled())
```

## Login and refresh flow

1. On the first request, `RestPyModule.login()` calls `auth_module.login()` only if
   `auth_module.token` is empty, then generates the headers.
2. If a request comes back 401 or 403 (`REFRESH_LOGIN_STATUS_CODES`),
   `login(refresh=True)` runs and the request is retried **exactly once**.
3. If login with `refresh=True` fails, `RestPyLoginException` is raised. If it fails
   without a refresh, the failure is only logged as an error.

## Writing your own auth module

```python
from restpy.auth.auth import RestPyAuthModule
from restpy.choices.request_method import RequestMethodChoice
from http import HTTPMethod


class MyApiKeyAuth(RestPyAuthModule):
    mode = "API_KEY"
    authorization_key = "X-Api-Key"
    authorization_value_format = "{token}"

    def __init__(self, *, api_key, **xtra_params):
        self.api_key = api_key
        super().__init__(**xtra_params)

    @property
    def token(self):
        return self.api_key

    def login(self, refresh=False):
        return bool(self.api_key)
```
