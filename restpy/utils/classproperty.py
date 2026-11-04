class classproperty:
    """
    Decorator that converts a method with a single cls argument into a property
    that can be accessed directly from the class.
    """

    def __init__(self, method=None):
        """`method` receives the class and returns the value."""
        self.fget = method

    def __get__(self, instance, cls=None):
        return self.fget(cls)

    def getter(self, method):
        """Set the getter when the decorator is used without arguments; returns the descriptor."""
        self.fget = method
        return self
