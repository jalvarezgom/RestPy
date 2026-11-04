# Getting started

## Requirements

- Python `3.12.*` (pinned in `pyproject.toml` via `requires-python = "==3.12.*"`)
- Runtime dependencies: `requests`, `xmltodict`

## Installation

From the repository, using [PDM](https://pdm-project.org/):

```bash
pdm install
```

Or with pip, from the bundled `requirements.txt`:

```bash
pip install -r requirements.txt
```

## The idea

With RestPy you don't write one function per endpoint. You declare **one class per API**,
**register** its endpoints once, and from then on you call them by name:

```python
api.get("summoner_by_name", url_params={"region": "europe", "gameName": "Voltait", "tagLine": "EUW"})
```

## Your first client

```python
from http import HTTPMethod

from restpy import RestPy
from restpy.auth.raw_token import RestPyAuthRawToken


class RiotAPI(RestPy):
    # Fixed-token authentication with a custom header
    auth_module = RestPyAuthRawToken(
        raw_token="RGAPI-xxxxxxxx",
        authorization_key="X-Riot-Token",
        authorization_value_format="{token}",
    )

    def register_urls(self):
        # Called automatically at the end of __init__
        self.register(
            name="me",
            url="/riot/account/v1/accounts/me",
            request_methods=[HTTPMethod.GET],
        )
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
    "region": "europe",
    "gameName": "Voltait",
    "tagLine": "EUW",
})

print(response.status_code)  # 200
print(response.data)         # dict already parsed from JSON
print(response.errors)       # None if everything went well
```

## Two ways to register endpoints

**A. Override `register_urls()`** (recommended): registration lives inside the class and
runs automatically on instantiation.

**B. Call `register()` from outside**, after creating the instance:

```python
api = RiotAPI(base_url="https://europe.api.riotgames.com")
api.register(name="me", url="/riot/account/v1/accounts/me", request_methods=[HTTPMethod.GET])
```

## Singleton client

`RestPySingleton` applies the singleton pattern: every instantiation returns the same
object and `__init__` only runs the first time. Useful for a global client shared across
the whole application.

```python
from restpy import RestPySingleton


class MyAPI(RestPySingleton):
    ...


a = MyAPI(base_url="https://api.example.com")
b = MyAPI()
assert a is b
```

## Logging

RestPy writes to the `restpy` logger; if that logger has no handlers, it falls back to
the root logger. To see the request, retry and login trace:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("restpy").setLevel(logging.DEBUG)
```
