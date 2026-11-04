# RestPy

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A declarative REST API client for Python. Instead of writing one function per endpoint,
you declare **one class per API**, register its routes once, and RestPy takes care of
authentication, retries, response parsing and HTTP status validation.

```python
from http import HTTPMethod

from restpy import RestPy
from restpy.auth.raw_token import RestPyAuthRawToken


class RiotAPI(RestPy):
    auth_module = RestPyAuthRawToken(
        raw_token="RGAPI-xxxxxxxx",
        authorization_key="X-Riot-Token",
        authorization_value_format="{token}",
    )

    def register_urls(self):
        self.register(
            name="summoner_by_name",
            url="/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}",
            request_methods=[HTTPMethod.GET],
            url_params=[
                {"name": "gameName", "is_required": True},
                {"name": "tagLine", "is_required": True},
            ],
        )


api = RiotAPI(
    base_url="https://{region}.api.riotgames.com",
    base_url_params=[{"name": "region", "is_required": True}],
)

response = api.get("summoner_by_name", url_params={
    "region": "europe", "gameName": "Voltait", "tagLine": "EUW",
})

print(response.status_code, response.data, response.errors)
```

## Features

- **Declarative endpoint registration** — name, parameterized route, allowed methods and
  data types in a single `register()` call.
- **Parameterized base URL** — `https://{region}.api.example.com` is resolved on every
  request.
- **Four built-in authentication modes**: raw token, Basic (username/password against a
  login endpoint), OAuth2 with a `refresh_token` persisted to file, and no
  authentication. Extensible with your own modules.
- **Automatic session refresh** — on a 401/403 the token is renewed and the request is
  retried once.
- **Configurable retries** — attempt count, back-off delay and the status codes that
  trigger them.
- **Automatic response parsing** — JSON, XML (via `xmltodict`) or plain text.
- **Errors as data, not exceptions** — request failures come back in `response.errors`
  so the caller decides; only configuration errors are raised.
- **Extensible status and payload validation** through exception runners.
- **Custom response managers** — `RESTpyResponse` subclasses that turn the body into
  domain objects.
- **Singleton mode** via `RestPySingleton` for a shared, application-wide client.

## Requirements

- Python `3.12`
- `requests`, `xmltodict`

## Installation

```bash
pdm install                     # with PDM (recommended)
pip install -r requirements.txt # with pip
```

## Documentation

The full documentation lives in [`docs/`](docs/README.md):

| Document | Contents |
|---|---|
| [Getting started](docs/getting-started.md) | Installation, first client, complete example |
| [Architecture](docs/architecture.md) | Packages, building blocks and the request lifecycle |
| [Authentication](docs/authentication.md) | `RestPyAuthModule` and the four built-in modes |
| [URLs and fields](docs/urls-and-fields.md) | `register()`, `RestPyURL`, `RESTpyField` |
| [Requests and responses](docs/requests-and-responses.md) | Verbs, retries, `RESTpyResponse`, `DataTypeChoice` |
| [Validators](docs/validators.md) | `BaseValidator` and the built-in validators |
| [Exceptions](docs/exceptions.md) | Hierarchy and validation runners |
| [API reference](docs/api-reference.md) | Public signatures and attributes |
| [Development](docs/development.md) | PDM environment, lint, tests |

## Development

```bash
pdm install
pdm run lint    # ruff check --fix + ruff format
pdm run test    # pytest
```

## License

MIT. See [LICENSE](LICENSE).

## Links

- Repository: https://github.com/jalvarezgom/RestPy
- Issues: https://github.com/jalvarezgom/RestPy/issues
