class RESTpyResponse:
    _response = None
    _data = None
    _processed_data = None
    errors = None

    def __init__(self, response, data=None, errors=None):
        self._response = response
        self._data = data
        self._processed_data = self._parse_data(data)
        self.errors = errors

    @property
    def data(self):
        return self._processed_data

    def _parse_data(self, data):
        if self.response is None or data is None or data == "":
            return None
        return data

    @property
    def url(self):
        return self.response.url if self.response is not None else None

    @property
    def response(self):
        return self._response

    @property
    def status_code(self):
        return self.response.status_code if self.response is not None else None

    def __str__(self):
        return f"RESTpyResponse(url={self.url}, status_code={self.status_code}, data={self.data}, errors={self.errors})"
