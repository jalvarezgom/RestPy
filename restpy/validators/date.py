from restpy.validators.base import DatetimeValidator


class DateYearMonthValidator(DatetimeValidator):
    """`YYYY-MM` date, sent as a `str`."""

    format_date = "%Y-%m"


class DateYearMonthDayValidator(DatetimeValidator):
    """`YYYY-MM-DD` date, sent as a `str`."""

    format_date = "%Y-%m-%d"


class DatetimeObjectValidator(DatetimeValidator):
    """ISO 8601 `str` or `datetime`, returned as a `datetime`. A JSON body cannot serialize that object."""

    _error_message = "Must be a datetime object or an ISO 8601 str"
    to_string = False
