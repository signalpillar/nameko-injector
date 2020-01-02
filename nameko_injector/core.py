import typing as t
import functools

import injector as inj
from nameko.containers import ServiceContainer, WorkerContext
from nameko.extensions import DependencyProvider


class RequestScope(inj.Scope):
    """A scope whose object lifetime is tied to a request."""

    def get(self, key: t.Any, provider: inj.Provider) -> t.Any:
        return provider


# rename to entrypoint_scope to follow naming of nameko
request = inj.ScopeDecorator(RequestScope)


class NamekoInjector(inj.Injector):
    def __init__(self, *, bindings: t.Mapping) -> None:
        super().__init__(modules=bindings.values())
        self.__bindings = bindings

    def decorate_service(self, service_cls):
        service_cls.injector = NamekoInjectorProvider(self)
        service_cls.__injector_bindings__ = self.__bindings

        for member_name in dir(service_cls):
            member = getattr(service_cls, member_name)
            if callable(member) and getattr(member, "nameko_entrypoints", 0):
                setattr(service_cls, member_name, self.inject(member))

        return service_cls

    def inject(self, fn):
        inj.inject(fn)

        @functools.wraps(fn)
        def decorated(*args, **kwargs):
            return self.call_with_injection(callable=fn, args=args, kwargs=kwargs)

        return decorated


class NamekoInjectorProvider(DependencyProvider):
    def __init__(self, injector):
        self._injector = injector

    def setup(self):
        self._injector.binder.bind(ServiceContainer, to=self.container)

    def get_dependency(self, worker_ctx):
        self._injector.binder.bind(WorkerContext, worker_ctx, scope=request)
        return self._injector
