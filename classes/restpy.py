from classes.module import RestPyModule
from utils.singleton_meta import SingletonClass


class RestPySingleton(SingletonClass, RestPyModule): ...


class RestPy(RestPyModule): ...
