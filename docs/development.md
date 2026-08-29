# Development

## Environment

The project uses [PDM](https://pdm-project.org/) for dependency and script management,
with the `pdm-backend` build backend.

```bash
pdm install          # runtime dependencies + dev groups (lint, test)
```

Development groups declared in `pyproject.toml`:

- `lint`: `ruff >= 0.5.5`
- `test`: `pytest >= 8.3.2`

## Scripts

```bash
pdm run lint    # ruff check --fix  +  ruff format
pdm run test    # pytest
```

## Style

Ruff configuration in `pyproject.toml`:

| Setting | Value |
|---|---|
| `line-length` | 150 |
| `indent-width` | 4 |
| `target-version` | `py311` |
| `select` | `E4`, `E7`, `E9`, `F` |
| `quote-style` | `double` |

Note: `target-version` is `py311` while `requires-python` is `==3.12.*`; the code uses
`http.HTTPMethod` and `enum.StrEnum`, both available from 3.11 onwards.

## Tests

```
tests/
├── conftest.py                # `api` fixture + FakeTransport/FakeResponse (offline transport)
├── test_restpy.py             # URL registration and lookup
├── test_module_behaviour.py   # the five verbs, lookup by path, per-client isolation
├── test_rpy_mocked.py         # full request cycle against a mocked transport
├── test_rpy_raw_token.py      # raw-token client, mocked
└── test_rpy_pokeapi.py        # integration: real requests against PokeAPI
```

Running them:

```bash
pdm run test                    # default suite: no network access
pytest tests/test_restpy.py -v
pytest -m integration           # only the tests that hit a real API
```

The default run excludes anything marked `@pytest.mark.integration` via
`addopts = "-m 'not integration'"` in `pyproject.toml`. Everything else is offline: the
`transport` fixture replaces `RequestMethodChoice.request` with a `FakeTransport` that
records each call (method, URL, params, headers) and replays the `FakeResponse` objects
queued by the test.

Writing a test that emits a request:

```python
def test_something(mock_api, transport):
    transport.queue(FakeResponse(200, {"name": "ditto"}))
    response = mock_api.get("mock_pokemon_by_name", url_params={"name": "ditto"})
    assert response.data["name"] == "ditto"
    assert transport.last_call.url == "https://pokeapi.test/api/v2/pokemon/ditto"
```

## Publishing

`pyproject.toml` declares `distribution = true`, so the package can be built with PDM:

```bash
pdm build
```

## Code organization

- One package per responsibility (`auth`, `validators`, `exceptions`, `choices`,
  `classes`, `utils`).
- The entire client logic lives in `RestPyModule`; `RestPy` and `RestPySingleton` are
  facades with no code of their own.
- Outstanding `TODO`s are marked in `restpy/classes/module.py`. See the
  [issue log](issues.md).
