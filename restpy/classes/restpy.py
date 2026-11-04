from restpy.classes.module import RestPyModule
from restpy.utils.singleton_meta import SingletonClass


class RestPySingleton(SingletonClass, RestPyModule):
    """`RestPyModule` that returns the same instance on every call; later constructor arguments are ignored."""


class RestPy(RestPyModule):
    """Ready-to-use `RestPyModule`. Instantiate it directly or subclass it to register endpoints."""
