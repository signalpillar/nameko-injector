import functools
import typing as t

import injector as inj
from nameko.containers import ServiceContainer, WorkerContext
from nameko.extensions import DependencyProvider


class RequestScope(inj.Scope):
    """A scope whose object lifetime is tied to a request."""

    def get(self, _: t.Any, provider: inj.Provider) -> t.Any:
        return provider


request_scope = inj.ScopeDecorator(RequestScope)


class NamekoInjector(inj.Injector):
    def decorate_service(self, service_cls):
        service_cls.injector = NamekoInjectorProvider(self)

        for member_name in dir(service_cls):
            member = getattr(service_cls, member_name)
            if callable(member) and getattr(member, "nameko_entrypoints", 0):
                setattr(service_cls, member_name, self.inject(member))

        return service_cls

    def inject(self, fn):
        inj.inject(fn)

        @functools.wraps(fn)
        def decorated(*args, **kwargs):
            # Instance of service that owns the entrypoint
            service_instance = args[0]
            # Child injector by NamekoInjectorProvider
            instance_injector = service_instance.injector
            # use it to resolve the dependencies
            return instance_injector.call_with_injection(
                callable=fn, args=args, kwargs=kwargs
            )

        return decorated


class NamekoInjectorProvider(DependencyProvider):
    def __init__(self, parent_injector: inj.Injector):
        # Bindings from the parent injector are shared between the calls.
        self.parent_injector = parent_injector

    def setup(self):
        # ServiceContainer is shared between the calls so it's in parent injector
        self.parent_injector.binder.bind(ServiceContainer, to=self.container)

    def get_dependency(self, worker_ctx):
        # Create child injector that will be used by decorated entrypoints.
        # Having child injector is something that will help us in testing.
        child_injector = self.parent_injector.create_child_injector()
        child_injector.binder.bind(WorkerContext, worker_ctx, scope=request_scope)
        return child_injector
