import json
import typing as t

import injector as inj
from nameko.containers import WorkerContext
from nameko.web.handlers import http

from nameko_injector.core import NamekoInjector, request


class ContainerConfig(t.NamedTuple):
    value: str


class ContainerRawConfigModule(inj.Module):

    def __init__(self, container) -> None:
        self.container = container

    @inj.provider
    def provider(self) -> ContainerConfig:
        return ContainerConfig(self.container.config)


class Metadata(t.NamedTuple):
    debug_id: str


class Config(t.NamedTuple):
    feature_x_enabled: bool


class ConfigModule(inj.Module):

    def __init__(self, scope):
        self._scope = scope

    def configure(self, binder) -> Config:
        binder.bind(Config, to=Config(feature_x_enabled=True), scope=self._scope)


class FailingConfigModule(inj.Module):

    @inj.provider
    def config_provider(self) -> Config:
        raise ValueError('Failed to create config')


class MetadataModule(inj.Module):
    def __init__(self, scope):
        self._scope = scope

    @inj.provider
    def provide(self) -> Metadata:
        return Metadata(debug_id='debug-id-provided')


INJECTOR = NamekoInjector(bindings=dict(
    config=ConfigModule(scope=inj.singleton),
    metadata=MetadataModule(scope=request),
))


@INJECTOR.decorate_service
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
