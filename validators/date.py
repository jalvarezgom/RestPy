from validators.base import DatetimeValidator


class DateYearMonthValidator(DatetimeValidator):
    format_date = '%Y-%m'

class DateYearMonthDayValidator(DatetimeValidator):
    format_date = '%Y-%m-%d'

class DatetimeObjectValidator(DatetimeValidator):
    to_string = False