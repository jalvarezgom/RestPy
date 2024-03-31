from classes.module import RestPyModule
from utils.singleton_meta import SingletonMeta


class RestPySingleton(RestPyModule, SingletonMeta):
    ...


class RestPy(RestPyModule):
    ...
