class RestPyException(Exception):
    """Base of every exception RestPy defines. `base_message` is the fixed part of `message`."""

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
    """Exception that also acts as a check: `validate(response)` returns an instance when the check fails.

    Subclasses implement `_validation`, returning True when the response is an error. Pass the
    class (not an instance) to the client's `add_exception_*_runner` methods.
    """

    @classmethod
    def _validation(cls, response, **xtra_params):
        """Return True when `response` should be reported as an error."""
        raise NotImplementedError("You must implement this method in your Exception.")

    @classmethod
    def validate(cls, response, raise_exception=False, **xtra_params):
        """Run the check.

        Returns:
            An instance of the exception when the check fails, otherwise None.

        Raises:
            The exception itself when the check fails and `raise_exception` is true.
        """
        exc = None
        if cls._validation(response, **xtra_params):
            exc = cls(cls.name)
        if raise_exception and exc:
            raise exc
        return exc
