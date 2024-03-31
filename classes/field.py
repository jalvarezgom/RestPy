class RESTpyField:
    is_query_params = False
    required = False
    validator = None

    def __init__(self, *, validator, is_query_params=False, required=False):
        self.is_query_params = is_query_params
        self.required = required
        self.validator = validator