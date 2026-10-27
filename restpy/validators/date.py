from restpy.validators.base import DatetimeValidator


class DateYearMonthValidator(DatetimeValidator):
    format_date = "%Y-%m"


class DateYearMonthDayValidator(DatetimeValidator):
    format_date = "%Y-%m-%d"


class DatetimeObjectValidator(DatetimeValidator):
    _error_message = "Must be a datetime object or an ISO 8601 str"
    to_string = False
