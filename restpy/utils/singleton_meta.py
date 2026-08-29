class SingletonMeta:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance


class SingletonClass(SingletonMeta):
    _is_init = False

    def __init__(self, headers: dict = None, base_url: str = None, base_url_params: list = None, auth_action=None):
        if not self._is_init:
            super().__init__(headers, base_url, base_url_params, auth_action)
            self._is_init = True
