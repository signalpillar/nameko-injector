from injector import inject, Injector, Scope


class RequestScope(Scope):
    """A scope whose object lifetime is tied to a request."""


