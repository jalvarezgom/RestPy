import requests

class RequestMethod():
    GET = 1
    POST = 2

    @staticmethod
    def request(method):
        methods = {
            RequestMethod.GET: requests.get,
            RequestMethod.POST: requests.post
        }
        return methods[method]