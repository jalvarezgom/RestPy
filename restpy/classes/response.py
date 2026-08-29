class RESTpyResponse:
    _response = None
    _data = None
    _processed_data = None
    errors = None

    def __init__(self, response, data=None, errors=None):
        self._response = response
        self._data = data
        if data:
            self._parse_data(data)
        self.errors = errors

    @property
    def data(self):
        if not self._processed_data:
            self._processed_data = self._parse_data(self._data) if self.response else None
        return self._processed_data

    def _parse_data(self, data):
        if self.status_code == 200:
            self._processed_data = data

    @property
    def url(self):
        return self.response.url if self.response else None

    @property
    def response(self):
        return self._response

    @property
    def status_code(self):
        return self.response.status_code if self.response else None

    def __str__(self):
        return f"RESTpyResponse(url={self.url}, status_code={self.status_code}, data={self.data}, errors={self.errors})"
