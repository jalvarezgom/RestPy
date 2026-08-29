# Validators

Validators normalize and check field values. They are attached to a `RESTpyField` through
the `validator` key when registering an endpoint.

```python
api.register(
    name="stats",
    url="/stats",
    request_methods=[HTTPMethod.GET],
    query_params=[
        {"name": "since", "validator": DateYearMonthDayValidator()},
        {"name": "limit", "validator": NumberValidator()},
    ],
)
```

> The declared validator is stored on the field, but request field validation is still
> incomplete in `RestPyModule._validate_request_fields()`. The validators are fully
> usable directly. See [RP-004](issues.md#rp-004).

## The contract: `BaseValidator`

```python
values, exception = MyValidator.validate(field_name, original_value)
```

- Returns a `(normalized_value, exception_or_None)` tuple.
- The exception is a `RestPyValidatorException`; it is **not raised**, it is returned.
- If `original_value` is `None`, it returns `(None, None)`: validators do not enforce
  presence — that is `RequiredFieldValidator`'s job.
- Lists are handled transparently: if the value is a list, each item is validated and a
  list is returned; otherwise a single value comes back. Errors accumulate, tagged with
  the index of the item that failed.

To write your own, implement `_run_validation()`, returning
`(converted_value, dict_of_message_fields)`, or `(None, dict)` when the value is invalid:

```python
from restpy.validators.base import BaseValidator


class EmailValidator(BaseValidator):
    _error_message = "Must be a valid email address."

    @classmethod
    def _run_validation(cls, value):
        if not isinstance(value, str) or "@" not in value:
            return (None, {})
        return (value.lower(), {})
```

`_error_message` supports `{...}` placeholders, filled from the `dict` returned by
`_run_validation()`.

## Built-in validators

| Class | Module | Behaviour |
|---|---|---|
| `StrValidator` | `validators/str.py` | Accepts `str`; converts numbers to `str`; rejects everything else. |
| `NumberValidator` | `validators/number.py` | Accepts any `numbers.Number`. |
| `ChoiceValidator` | `validators/base.py` | Checks the value is in `_choice_class`. Subclass it and set `_choice_class`. |
| `DatetimeValidator` | `validators/base.py` | Converts between `datetime` and `str` according to `format_date` and `to_string`. |
| `IgnoreCaseValidator` | `validators/base.py` | Validates nothing: accepts any value. Useful as a placeholder. |
| `DateYearMonthValidator` | `validators/date.py` | `DatetimeValidator` with format `%Y-%m`. |
| `DateYearMonthDayValidator` | `validators/date.py` | `DatetimeValidator` with format `%Y-%m-%d`. |
| `DatetimeObjectValidator` | `validators/date.py` | `DatetimeValidator` with `to_string = False`: returns `datetime` objects. |
| `RequiredFieldValidator` | `validators/required_field.py` | Checks that a field marked as required has a value. |

### `DatetimeValidator`

- `format_date`: the `strftime`/`strptime` format used for conversion.
- `to_string = True` (default): the output is a string formatted with `format_date`.
- `to_string = False`: the output is a `datetime` object; a `str` input is rejected.

```python
from restpy.validators.base import DatetimeValidator


class SpanishDateValidator(DatetimeValidator):
    format_date = "%d/%m/%Y"
```

### `ChoiceValidator`

```python
from restpy.validators.base import ChoiceValidator


class RegionValidator(ChoiceValidator):
    _choice_class = ["europe", "americas", "asia"]
```

### `RequiredFieldValidator`

It is used differently from the rest: it takes the `RESTpyField` and the data dictionary,
not a name/value pair.

```python
value, error = RequiredFieldValidator.validate(rp_field, url_params)
```

If the field is not required it returns `(None, None)` without checking anything.
