class RESTpyException(Exception):
    """Base exception class."""
    base_message = None

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def message(self):
        return f"[RESTpy] Exception:{self.base_message} | {self}"