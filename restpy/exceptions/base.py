class RestPyException(Exception):
    """Base exception class."""

    base_message = None

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def message(self):
        return f"[RESTpy] Exception:{self.base_message} | {self}"

    def __repr__(self):
        return self.message


class RestPyRunnerException(RestPyException):
    @classmethod
    def _validation(cls, response, **xtra_params):
        raise NotImplementedError("You must implement this method in your Exception.")

    @classmethod
    def validate(cls, response, raise_exception=False, **xtra_params):
        exc = None
        if cls._validation(response, **xtra_params):
            exc = cls(cls.name)
        if raise_exception and exc:
            raise exc
        return exc
