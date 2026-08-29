# URLs and fields

## `register()`

Registers an endpoint on the client. It is the heart of the declarative side.

```python
api.register(
    name="summoner_by_name",
    url="/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}",
    request_methods=[HTTPMethod.GET],
    request_data_type=DataTypeChoice.DICT,
    url_params=[{"name": "gameName", "is_required": True}],
    query_params=[{"name": "page", "validator": NumberValidator}],
    data_params=[{"name": "body_field", "is_required": True}],
    response_data_type=DataTypeChoice.JSON,
    response_manager=MyResponse,
)
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | `str` | in practice, yes | Identifier the endpoint will be called by. Must be unique. |
| `url` | `str` | **yes** | Path relative to `base_url` (or an absolute URL when there is no `base_url`). Supports `{param}` placeholders. |
| `request_methods` | `List[HTTPMethod]` | **yes** | Allowed verbs. A verb not listed returns `RestPyRequestMethodException`. |
| `request_data_type` | `DataTypeChoice` | no | How to serialize the body. Defaults to `default_request_data_type` (`DICT`). |
| `url_params` | `List[Dict]` | no | Path parameters. `_base_url_params` is always prepended. |
| `query_params` | `List[Dict]` | no | Query string parameters. |
| `data_params` | `List[Dict]` | no | Body fields. |
| `response_data_type` | `DataTypeChoice` | no | How to parse the response. Defaults to `default_response_data_type` (`JSON`). |
| `response_manager` | `RESTpyResponse` class | no | Class wrapping the result. Defaults to `default_response_manager`. |

Registration errors (all `ValueError`):

- `url` missing or not a `str`
- `request_methods` missing, not a list, or containing non-`HTTPMethod` items
- `url_params` / `query_params` / `data_params` containing non-`dict` items
- `request_data_type` / `response_data_type` that are not `str`
- `response_manager` passed as an *instance* rather than a *class*
- `name` already registered on this client

## `base_url` and `base_url_params`

`base_url` is prepended to each endpoint's `url` and may carry placeholders of its own:

```python
api = MyAPI(
    base_url="https://{region}.api.riotgames.com",
    base_url_params=[{"name": "region", "is_required": True}],
)
```

`base_url_params` is automatically added to the `url_params` of **every** endpoint
registered afterwards, so `region` is resolved on each call without repeating it.

It can also be set later with `set_base_url()`, although that does not reassign
`base_url_params` on already-registered URLs.

## `RESTpyField`

Each entry in `url_params`, `query_params` or `data_params` is a `dict` that becomes a
`RESTpyField`:

| Key | Type | Description |
|---|---|---|
| `name` | `str` | **Required.** Field name; for path parameters it must match the `{...}` placeholder. |
| `is_required` | `bool` | Whether the field is mandatory. Defaults to `False`. |
| `validator` | `BaseValidator` instance | Validator attached to the field. Optional. |

The location (`where_data`) is assigned by `register()` automatically, based on the list
the field was declared in:

| List | `RestPyFieldWhereData` | Value |
|---|---|---|
| `url_params` | `URL_PARAMS` | `"URI"` |
| `query_params` | `QUERY_PARAMS` | `"QUERY"` |
| `data_params` | `BODY` | `"BODY"` |

## `RestPyURL`

The object representing a registered endpoint.

| Member | Description |
|---|---|
| `name`, `url` | Identifier and path template. |
| `request_methods` | List of allowed `HTTPMethod`s. |
| `request_data_type`, `response_data_type` | Inbound and outbound data types. |
| `response_manager` (property) | Response wrapper class. |
| `fields_list` (property) | All fields on the endpoint. |
| `url_fields` (`cached_property`) | Fields with `where_data == URI`. |
| `query_fields` (`cached_property`) | Fields with `where_data == QUERY`. |
| `data_fields` (`cached_property`) | Fields with `where_data == BODY`. |
| `get_field(name)` | Returns a field by name, or `None`. |

`RestPyURL` keeps a `_used_names` set **at class level**: an endpoint name must be unique
across the whole process, not just within one client. Registering the same name twice —
even on different clients — raises `ValueError`. See [RP-007](issues.md#rp-007).

## Looking endpoints up

```python
url = api.search_url(name="summoner_by_name")                 # by name (recommended)
url = api.search_url(url_str="/riot/account/v1/accounts/me")  # by path
```

Without `name` or `url_str` it raises `ValueError`. When nothing is found it logs a debug
message and returns `None`; the corresponding request then returns a `RESTpyResponse`
with `RestPyURLNotFoundException` in `errors`.

You can also inspect the `api.registered_urls` dictionary directly.

## Path parameter substitution

`_generate_url_params_url()` walks the endpoint's `url_fields`, pulls the values from the
`url_params` passed to the call and applies `url.format(**values)`. Consumed values are
removed from the dictionary; the leftovers remain available to the
`_apply_custom_data_to_pre_url` / `_apply_custom_data_to_post_url` hooks.
