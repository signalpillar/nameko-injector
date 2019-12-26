import typing as t
import pytest
import functools
import json
import eventlet
from nameko.web.handlers import http
from eventlet import corolocal

from nameko.extensions import DependencyProvider
from injector import Injector, Scope, singleton, Module
import injector as inj

from nameko.containers import ServiceContainer, WorkerContext

# request-scope developed first?
# provide nameko request-scope dependencies (worker context, request for HTTP)


class RequestScope(Scope):
    """A scope whose object lifetime is tied to a request."""

    def get(self, key: t.Any, provider: inj.Provider) -> t.Any:
        return provider


# rename to entrypoint_scope to follow naming of nameko
request = inj.ScopeDecorator(RequestScope)


class ContainerConfig(t.NamedTuple):
    value: str


class ContainerRawConfigModule(inj.Module):

    def __init__(self, container) -> None:
        self.container = container

    @inj.provider
    def provider(self) -> ContainerConfig:
        return ContainerConfig(self.container.config)


@pytest.fixture(autouse=True)
def service(runner_factory, web_config):
    service_config = web_config
    runner = runner_factory(service_config, Service)
    runner.start()
    yield
    runner.stop()


class Metadata(t.NamedTuple):
    debug_id: str


class Config(t.NamedTuple):
    feature_x_enabled: bool


class ConfigModule(Module):
    def __init__(self, scope):
        self._scope = scope

    def configure(self, binder):
        binder.bind(Config, to=Config(feature_x_enabled=True))


class MetadataModule(Module):
    def __init__(self, scope):
        self._scope = scope

    @inj.provider
    def provide(self) -> Metadata:
        return Metadata(debug_id='debug-id-provided')


class NamekoInjector(inj.Injector):

    def decorate_service(self, service_cls):
        service_cls.injector_bindings = NamekoInjectorProvider(self)

        for member_name in dir(service_cls):
            member = getattr(service_cls, member_name)
            if callable(member) and getattr(member, 'nameko_entrypoints', 0):
                setattr(service_cls, member_name, self.inject(member))

        return service_cls

    def inject(self, fn):
        inj.inject(fn)

        @functools.wraps(fn)
        def decorated(*args, **kwargs):
            return self.call_with_injection(
                callable=fn, args=args, kwargs=kwargs
            )
        return decorated


injector = NamekoInjector(modules=[
    ConfigModule(scope=inj.singleton),
    MetadataModule(scope=request),
])


class NamekoInjectorProvider(DependencyProvider):

    def __init__(self, injector):
        self._injector = injector

    def setup(self):
        self._injector.binder.bind(ServiceContainer, to=self.container)

    def get_dependency(self, worker_ctx):
        self._injector.binder.bind(WorkerContext, worker_ctx, scope=request)
        return self._injector


# there are 3 possible ways to decorate service
# 1) @injector.inject each method explicitly. Will work but doesn't support
# request-scope without requiring clients of the lib to add dependency provider
# manually.
# 2) @injector.inject service class. This way the class will get dependency
# provider authomatically. The provider will be mocked during the testing so
# the we need to explore it better.
# 3) Extend custom class that decorates the methods and adds the provider.

@injector.decorate_service
class Service:

    name = 'test-service'

    @http('GET', '/config')
    def view_singleton_config(self, request, config: Config):
        return json.dumps({
            'feature_x': config.feature_x_enabled,
            'id': id(config),
        })

    @http('GET', '/worker/context/<int:id_>')
    def view_worker_context(self, request, id_, context: WorkerContext):
        return json.dumps(dict(
            service_name=context.service_name,
            call_id=context.call_id,
            id=id_,
        ))

# Testing
# test http injection and request scope
# test RPC injection and request scope

def test_singleton_config_injected(web_session):
    # make 2 calls on the service to ensure we get the same instance of the
    # config.
    responses = [web_session.get('/config') for _ in range(2)]
    assert {200} == {r.status_code for r in responses}
    data = {r.json()['id'] for r in responses}
    assert 1 == len(data)


def test_request_scoped_injected(web_session):
    threads = [
        eventlet.spawn(web_session.get, f'/worker/context/{id_}')
        for id_ in range(10)
    ]
    responses = [t.wait() for t in threads]
    assert {200} == {r.status_code for r in responses}
    all_call_ids = {r.json()['call_id'] for r in responses}
    assert 10 == len(all_call_ids)


def test_error_raised_during_injection_http():
    ...


def test_error_raised_during_injection_rpc():
    ...
