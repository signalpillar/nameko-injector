import functools
import logging
import typing as t
from weakref import WeakKeyDictionary
import itertools

import injector as inj
from eventlet import corolocal
from nameko.containers import ServiceContainer, WorkerContext
from nameko.extensions import DependencyProvider

_LOGGER = logging.getLogger(__name__)


class RequestScope(inj.Scope):
    """A scope whose object lifetime is tied to a request."""

    def configure(self) -> None:
        # Only eventlet at the moment though there is greenlet support on the roadmap.
        # The type of locals is the only difference between this implementation and
        # injector.ThreadLocalScope
        self._locals = corolocal.local()

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
        # Mapping of a worker context to child injector created for it.
        # We need to be able to look up injector in different stages of the worker
        # live-cycle.
        self._injector_by_worker_ctx: WeakKeyDictionary = WeakKeyDictionary()

    def setup(self):
        # ServiceContainer is shared between the calls so it's in parent injector
        self.parent_injector.binder.bind(
            ServiceContainer, to=self.container, scope=inj.singleton
        )

    def get_dependency(self, worker_ctx):
        # Create child injector that will be used by decorated entrypoints.
        # Having child injector is something that will help us in testing and also
        # isolate request-level dependencies bound per entry-point.
        child_injector = self.parent_injector.create_child_injector()
        child_injector.binder.bind(WorkerContext, worker_ctx, scope=request_scope)
        self._injector_by_worker_ctx[worker_ctx] = child_injector
        return child_injector

    def worker_teardown(self, worker_ctx):
        """Called after a service worker has executed a task."""
        # It's a good time to free resources in the request scope.
        # Intentionally do not fallback to None if worker_ctx is not found. The service
        # call won't fail but error should be reported in the logs.
        child_injector = self._injector_by_worker_ctx.pop(worker_ctx)
        # Normally, only when testing, child scope can have some resources. In the real
        # app everything will be bound on the level of class injector (parent binder).
        child_scope = child_injector.get(ResourceAwareRequestScope)
        parent_scope = child_injector.parent.get(ResourceAwareRequestScope)

        for closable in itertools.chain(
            child_scope.iter_closable(), parent_scope.iter_closable()
        ):
            try:
                closable.close()
            except Exception:
                _LOGGER.exception(
                    "Failed to close request-scoped resource %r on worker teardown. "
                    "Will attempt to close the rest of resources in the request scope.",
                    closable.__class__,
                )
