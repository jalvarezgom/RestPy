# RestPy documentation

RestPy is a Python library that lets you declare a REST API client declaratively: you
define one class per domain/API, register its endpoints with their parameters, and the
library handles authentication, retries, response parsing and HTTP status validation.

## Index

| Document | Contents |
|---|---|
| [Getting started](getting-started.md) | Installation, first client, complete example |
| [Architecture](architecture.md) | Packages, building blocks and the request lifecycle |
| [Authentication](authentication.md) | `RestPyAuthModule` and the four built-in modes |
| [URLs and fields](urls-and-fields.md) | `register()`, `RestPyURL`, `RESTpyField`, parameter kinds |
| [Requests and responses](requests-and-responses.md) | Verbs, retries, login refresh, `RESTpyResponse`, `DataTypeChoice` |
| [Validators](validators.md) | `BaseValidator` and the built-in validators |
| [Exceptions](exceptions.md) | Exception hierarchy and validation runners |
| [API reference](api-reference.md) | Public signatures and attributes |
| [Development](development.md) | PDM environment, lint, tests |
| [Issue log](issues.md) | The 22 issues found, in ticket form |

## Project status

Version `1.0.0` as declared in `pyproject.toml`. The core (URL registration,
authentication, retries, parsing) is implemented; request field validation is only
partially implemented and marked with `TODO` in the code. Read the
[issue log](issues.md) before using this in production.
