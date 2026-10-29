from restpy.validators.base import BaseValidator


class RequiredFieldValidator(BaseValidator):
    _base_message = "Field: {field_name} | MSG:"
    _error_message = "Field is required"

    @classmethod
    def _validate(cls, rp_field, data):
        if not rp_field.required:
            return (None, None)
        value = data.get(rp_field.name, None)

        (error_fields, error_msg) = {}, None
        if value is None or (value == "" and not rp_field.allow_empty):
            error_fields["field_name"] = rp_field.name
            error_fields["value"] = value
            error_msg = cls.get_error_message(error_fields, error_msg=cls.error_message())
        return (value, error_msg)
