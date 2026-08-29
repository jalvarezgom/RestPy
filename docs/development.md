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
├── test_restpy.py         # URL registration and lookup
└── test_rpy_raw_token.py  # client against the Riot API with a raw token
```

Running them:

```bash
pdm run test
# or
pytest tests/test_restpy.py -v
```

Current state of the suite:

- `tests/test_restpy.py` depends on an `api` fixture that is not defined in any
  `conftest.py`: those tests error out with a fixture-not-found failure.
- `tests/test_rpy_raw_token.py` performs real requests against `api.riotgames.com` with a
  development key hard-coded in the file, and its assertions check `RestPyURL` attributes
  on what is actually a `RESTpyResponse`.

Before growing the coverage it is worth adding a `conftest.py` with the shared fixtures
and replacing the network calls with mocked responses.

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
