from http import HTTPMethod

import requests


class RequestMethodChoice:
    @staticmethod
    def request(method):
        methods = {
            HTTPMethod.GET: requests.get,
            HTTPMethod.POST: requests.post,
            HTTPMethod.PUT: requests.put,
            HTTPMethod.PATCH: requests.patch,
            HTTPMethod.DELETE: requests.delete,
            HTTPMethod.HEAD: requests.head,
            HTTPMethod.OPTIONS: requests.options,
        }
        return methods[method]
