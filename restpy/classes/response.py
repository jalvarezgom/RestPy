class RESTpyResponse:
    """What every request returns: the raw response, the parsed data and the errors found.

    Subclass it and pass it as `response_manager` to `register()` to shape the result.

    Attributes:
        errors: List of exceptions, or None when the request succeeded.
    """

    _response = None
    _data = None
    _processed_data = None
    errors = None

    def __init__(self, response, data=None, errors=None):
        """
        Args:
            response: The `requests.Response`, or None when no request was sent.
            data: The parsed body.
            errors: Exceptions collected while preparing, sending or validating the request.
        """
        self._response = response
        self._data = data
        self._processed_data = self._parse_data(data)
        self.errors = errors

    @property
    def data(self):
        """The parsed body, or None when there is no response or the body is empty."""
        return self._processed_data

    def _parse_data(self, data):
        """Hook that post-processes the parsed body. Override it to reshape `data`."""
        if self.response is None or data is None or data == "":
            return None
        return data

    @property
    def url(self):
        """Final URL of the response, or None when no request was sent."""
        return self.response.url if self.response is not None else None

    @property
    def response(self):
        """The underlying `requests.Response`, or None when no request was sent."""
        return self._response

    @property
    def status_code(self):
        """HTTP status the server returned, or None when no request was sent."""
        return self.response.status_code if self.response is not None else None

    def __str__(self):
        return f"RESTpyResponse(url={self.url}, status_code={self.status_code}, data={self.data}, errors={self.errors})"
