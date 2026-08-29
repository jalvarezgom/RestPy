from restpy.classes.module import RestPyModule
from restpy.utils.singleton_meta import SingletonClass


class RestPySingleton(SingletonClass, RestPyModule): ...


class RestPy(RestPyModule): ...
