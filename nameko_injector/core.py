import functools
import logging
import typing as t

import injector as inj
from eventlet import corolocal
from nameko.containers import ServiceContainer, WorkerContext
from nameko.extensions import DependencyProvider
from werkzeug.wrappers import Request

_LOGGER = logging.getLogger(__name__)


class BaseError(Exception):
    """Base error type for this library."""


class RequestScope(inj.Scope):
    """A scope whose object lifetime is tied to a request."""

    def configure(self) -> None:
        # Only eventlet at the moment though there is greenlet support on the roadmap.
        # The type of locals is the only difference between this implementation and
        # injector.ThreadLocalScope
        self._locals = corolocal.local()

    def _set(self, interface: t.Any, provider: inj.Provider) -> None:
        # protected and shouldn't be used outside of the library
        setattr(self._locals, repr(interface), provider)

    def get(self, interface: t.Any, provider: inj.Provider) -> inj.Provider:
        key = repr(interface)
        try:
            return getattr(self._locals, key)
        except AttributeError:
            provider = inj.InstanceProvider(provider.get(self.injector))
            setattr(self._locals, key, provider)
            return provider


class ResourceAwareRequestScope(RequestScope):
    """Scope that is similar to RequestScope but is aware about resources.

    Resource is a instance created in this scope that has 'close' method. This method
    will be called in the end of the request.
    """

    def iter_closable(self):
        for provider in vars(self._locals).values():
            if isinstance(provider, inj.InstanceProvider):
                inst = provider.get(self.injector)
                if hasattr(inst, "close"):
                    yield inst


request_scope = inj.ScopeDecorator(RequestScope)
# In this early stage of the project it's decided to have a separate scope instead of
# supporting the case in the existing `RequestScope`.
resource_request_scope = inj.ScopeDecorator(ResourceAwareRequestScope)


class MissingInRequestScopeError(BaseError):
    def __init__(self, interface):
        super().__init__(
            f"{interface} not found in the current request scope. "
            "It means nameko_injector.NamekoInjectorProvider didn't work. "
            "Ensure the dependency provider is present in the service "
            "or not mocked when testing."
        )

    def provider(self):
        raise self


class NamekoInjector(inj.Injector):
    def __init__(self, modules, *args, **kwargs):
        super().__init__(modules, *args, **kwargs)
        self._modules = modules
        # This instance of injector will be shared between the service calls.
        # NamekoInjectorProvider has a special logic to ensure that instances of these
        # interfaces are injected properly from the request_scope.
        # We still need to bind the interfaces so the injector knows what scope to use
        # and also when provider didn't work provide a meaningful error.
        self.binder.bind(
            Request,
            to=MissingInRequestScopeError(Request).provider,
            scope=request_scope,
        )
        self.binder.bind(
            WorkerContext,
            to=MissingInRequestScopeError(WorkerContext).provider,
            scope=request_scope,
        )

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
    def __init__(self, injector: NamekoInjector):
        self.injector = injector

    def setup(self):
        self.injector.binder.bind(
            ServiceContainer, to=self.container, scope=inj.singleton
        )

    def get_dependency(self, worker_ctx):
        # The injector is shared between the service calls therefore we cannot use bind
        # InstanceProvider with the binder. Binding to a specific instance in one call
        # may lead to a reference in another call (scope calls provider and gets
        # incorrect instance).
        # Put the instances of Request and WorkerContext directly in the
        # request scope. As this dependency provider runs in scope of a call coroutine
        # it's safe to access corolocal storage in the scope.
        scope_binding, _ = self.injector.binder.get_binding(RequestScope)
        scope_instance = scope_binding.provider.get(self.injector)

        scope_instance = self.injector.get(request_scope.scope)
        scope_instance._set(WorkerContext, inj.InstanceProvider(worker_ctx))
        if worker_ctx.args and isinstance(worker_ctx.args[0], Request):
            request = worker_ctx.args[0]
            scope_instance._set(Request, inj.InstanceProvider(request))
        return self.injector

    def worker_teardown(self, worker_ctx):
        """Called after a service worker has executed a task."""
        scope = self.injector.get(ResourceAwareRequestScope)
        for closable in scope.iter_closable():
            try:
                closable.close()
            except Exception:
                _LOGGER.exception(
                    "Failed to close request-scoped resource %r on worker teardown. "
                    "Will attempt to close the rest of resources in the request scope.",
                    closable.__class__,
                )
