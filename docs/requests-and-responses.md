# Requests and responses

## Available verbs

```python
api.get(name, url_str=None, url_params={}, query_params={}, data_params={}, **xtra_params)
api.post(name, url_params={}, query_params={}, data_params={})
api.put(name, url_params={}, query_params={}, data_params={})
api.patch(name, url_params={}, query_params={}, data_params={})
api.delete(name, url_params={}, query_params={}, data_params={})
```

| Argument | Purpose |
|---|---|
| `name` | Name of the registered endpoint. |
| `url_str` | Alternative to `name`: look the endpoint up by path (`get` only). |
| `url_params` | Values for the `{...}` placeholders in `base_url` and in the path. |
| `query_params` | Passed straight through to `requests` as `params`. |
| `data_params` | Request body; serialized according to `request_data_type`. |

All of them return an instance of `response_manager` (`RESTpyResponse` by default).

> Only `get()` accepts `url_str` today; the other verbs have a signature that is
> incompatible with the internal engine. See [RP-001](issues.md#rp-001).

## Retries and session refresh

Configurable as `RestPyModule` class attributes:

| Attribute | Default | Description |
|---|---|---|
| `RETRIES_URL` | `3` | Maximum attempts per request. |
| `RETRIES_TIMEOUT_SECONDS` | `1` | Delay between attempts when the status is a timeout. |
| `RETRIES_TIMEOUT_STATUS_CODES` | `[408, 504]` | Statuses that trigger a retry **with** a delay. |
| `RETRIES_STATUS_CODES` | `[408, 504]` | Statuses that trigger a retry. |
| `REFRESH_LOGIN_STATUS_CODES` | `[401, 403]` | Statuses that trigger `login(refresh=True)`. |

The login refresh happens **once per request**: if the response is 401/403 again after
renewing the token, no further attempt is made.

Retries after the first one reuse `response.request.url`, that is, the already-resolved
URL from the previous attempt.

## Valid status codes

```python
_VALID_STATUS = [HTTPStatus.OK, HTTPStatus.CREATED, HTTPStatus.NO_CONTENT, HTTPStatus.RESET_CONTENT]
```

Adjustable at runtime:

```python
api.add_valid_status(HTTPStatus.ACCEPTED)
api.remove_valid_status(HTTPStatus.RESET_CONTENT)
```

If the status is not in the list, the `_EXCEPTION_VALID_STATUS_RUNNER` runners fire
(`[RestPyIsSuccessResponse]` by default) and the first exception produced is returned in
`RESTpyResponse.errors`.

In addition, if `response_data_type` is `JSON` and the body does not start with `{`, the
status is rewritten to `204 NO_CONTENT` and a log entry is emitted.

## Response validators

```python
api.add_exception_valid_status_runner(MyStatusException)
api.add_exception_valid_response_runner(MyPayloadException)
api.remove_exception_valid_status_runner(MyStatusException)
api.remove_exception_valid_response_runner(MyPayloadException)
```

Both accept classes derived from `RestPyRunnerException` (see
[Exceptions](exceptions.md)).

> `add_*` checks with `isinstance(exception_runner, RestPyRunnerException)`, which
> requires an **instance**, while `_validator_runner()` calls `validate()` as a class
> method. See [RP-005](issues.md#rp-005).

## `DataTypeChoice`

Constants: `JSON = "json"`, `XML = "xml"`, `TEXT = "text"`, `DICT = "dict"`.

### Request serialization — `parse_request(type, data)`

| Type | Headers added | Body sent |
|---|---|---|
| `JSON` | `Content-Type: application/json` | `json.dumps(data)` |
| Anything else | none | `data` untouched |

### Response parsing — `parse_response(type, response)`

Returns `response.text` as-is when the status is `204`, when the body is empty, or when
the type is `JSON` and the body does not start with `{`. Otherwise:

| Type | Result |
|---|---|
| `JSON` | `response.json()` |
| `XML` | `xmltodict.parse(response.text)` (or `{}` for an empty body) |
| Other | raises `RestPyResponseTypeException` |

## `RESTpyResponse`

```python
response = api.get("me", url_params={"region": "europe"})

response.status_code  # HTTP status, or None if no request was made
response.url          # final resolved URL, or None
response.data         # parsed body (only populated on status 200)
response.errors       # list of exceptions, or None
response.response     # the raw `requests` Response object
```

`data` is computed lazily, and `_parse_data()` only assigns the result when the status is
exactly `200`; for other valid codes (201, 204…) `data` stays `None` and the raw body
remains reachable via `response.response.text`.

`errors` is **not raised**: you have to check it explicitly.

```python
if response.errors:
    for error in response.errors:
        print(error.message)
```

### Custom response manager

```python
from restpy import RESTpyResponse


class UsersResponse(RESTpyResponse):
    def _parse_data(self, data):
        if self.status_code == 200:
            self._processed_data = [User(**item) for item in data["results"]]


api.register(
    name="users",
    url="/users",
    request_methods=[HTTPMethod.GET],
    response_manager=UsersResponse,  # the class, not an instance
)
```

It can also be set for the whole client via `default_response_manager = UsersResponse`.

## Headers

The headers sent with each request are the merge, in this order, of:

1. `self.headers` (class attribute or the constructor's `headers` argument)
2. `auth_module.auth_headers`
3. Whatever `DataTypeChoice.parse_request()` contributes for the given
   `request_data_type`

Cookies are taken from `auth_module.cookies`.
