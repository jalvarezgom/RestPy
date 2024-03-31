from validators.base import BaseValidator


class RequiredFieldValidator(BaseValidator):
    _base_message = 'Field: {field_name} | MSG:'
    _error_message = 'Field is required'

    @classmethod
    def _validate(cls, fparam, field_and_params):
        if not fparam.required:
            return None, None
        params = field_and_params[1]
        field_name = field_and_params[0]
        value = params.get(field_name, None)

        error_fields, error_msg = {}, None
        if not value:
            error_fields['field_name'] = field_name
            error_fields['value'] = value
            error_msg = cls.get_error_message(error_fields, error_msg=cls.error_message())
        return value, error_msg