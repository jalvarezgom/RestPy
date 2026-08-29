from http import HTTPMethod

import requests

METHOD_FUNCTION_NAMES = {
    HTTPMethod.GET: "get",
    HTTPMethod.POST: "post",
    HTTPMethod.PUT: "put",
    HTTPMethod.PATCH: "patch",
    HTTPMethod.DELETE: "delete",
    HTTPMethod.HEAD: "head",
    HTTPMethod.OPTIONS: "options",
}


class RequestMethodChoice:
    @staticmethod
    def request(method, session=None):
        """Resolve the verb against `session`, or against the `requests` module when there is none.

        A `requests.Session` reuses the underlying TCP connection between calls to the same
        host; the module-level functions open and close one per request.
        """
        return getattr(session if session is not None else requests, METHOD_FUNCTION_NAMES[method])
