import datetime
from enum import StrEnum

import pytest

from restpy.exceptions import RestPyValidatorException
from restpy.validators import (
    BaseValidator,
    ChoiceValidator,
    DateYearMonthValidator,
    IgnoreCaseValidator,
    NumberValidator,
    StrValidator,
)


class Color(StrEnum):
    RED = "red"
    BLUE = "blue"


class ColorValidator(ChoiceValidator):
    _choice_class = Color


class TestBaseValidator:
    def test_subclasses_must_implement_the_check(self):
        with pytest.raises(NotImplementedError):
            BaseValidator.validate("field", 1)

    @pytest.mark.parametrize("validator", [ColorValidator, NumberValidator, StrValidator, IgnoreCaseValidator, DateYearMonthValidator])
    def test_none_is_not_validated(self, validator):
        assert validator.validate("field", None) == (None, None)

    def test_empty_list_is_valid(self):
        assert StrValidator.validate("field", []) == ([], None)


class TestChoiceValidator:
    def test_member_passes(self):
        assert ColorValidator.validate("color", "red") == ("red", None)

    def test_non_member_is_rejected(self):
        value, error = ColorValidator.validate("color", "green")
        assert value is None
        assert isinstance(error, RestPyValidatorException)
        assert "valid choices" in str(error)

    def test_list_of_members_passes(self):
        assert ColorValidator.validate("color", ["red", "blue"]) == (["red", "blue"], None)

    def test_list_reports_each_wrong_index(self):
        values, error = ColorValidator.validate("color", ["red", "green", "pink"])
        assert values == ["red", None, None]
        assert "Errors found:" in str(error)
        assert "idx: 1" in str(error) and "idx: 2" in str(error)
        assert "idx: 0" not in str(error)


class TestNumberValidator:
    @pytest.mark.parametrize("value", [0, 3, 2.5])
    def test_numbers_pass(self, value):
        assert NumberValidator.validate("n", value) == (value, None)

    def test_string_is_rejected(self):
        value, error = NumberValidator.validate("n", "5")
        assert value is None
        assert isinstance(error, RestPyValidatorException)

    def test_one_bad_item_in_a_list_is_reported(self):
        values, error = NumberValidator.validate("n", [1, "a"])
        assert values == [1, None]
        assert "idx: 1" in str(error)


class TestStrValidator:
    def test_string_passes(self):
        assert StrValidator.validate("s", "abc") == ("abc", None)

    def test_number_is_cast_to_string(self):
        assert StrValidator.validate("s", 5) == ("5", None)
        assert StrValidator.validate("s", 2.5) == ("2.5", None)

    @pytest.mark.parametrize("value", [{}, object(), (1, 2)])
    def test_other_types_are_rejected(self, value):
        result, error = StrValidator.validate("s", value)
        assert result is None
        assert isinstance(error, RestPyValidatorException)


class TestIgnoreCaseValidator:
    def test_value_is_passed_through(self):
        assert IgnoreCaseValidator.validate("s", "AnyThing") == ("AnyThing", None)


class TestDateYearMonthValidator:
    def test_valid_string_is_kept(self):
        assert DateYearMonthValidator.validate("d", "2024-03") == ("2024-03", None)

    def test_datetime_is_formatted(self):
        assert DateYearMonthValidator.validate("d", datetime.datetime(2024, 3, 15)) == ("2024-03", None)

    def test_wrong_format_is_rejected(self):
        value, error = DateYearMonthValidator.validate("d", "2024-03-15")
        assert value is None
        assert isinstance(error, RestPyValidatorException)

    def test_list_of_dates(self):
        assert DateYearMonthValidator.validate("d", ["2024-01", "2024-02"]) == (["2024-01", "2024-02"], None)
