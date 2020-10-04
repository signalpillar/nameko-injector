import json
import typing as t

import injector as inj
from nameko.containers import WorkerContext
from nameko.web.handlers import http

from nameko_injector.core import NamekoInjector, request_scope


class Metadata(t.NamedTuple):
    debug_id: str


class Config(t.NamedTuple):
    feature_x_enabled: bool


@inj.provider
def provide_working_config() -> Config:
    return Config(feature_x_enabled=True)


@inj.provider
def provide_failing_config() -> Config:
    raise ValueError("Failed to create config")


@inj.provider
def provide_metadata() -> Metadata:
    return Metadata(debug_id="debug-id-provided")


def configure_bindings(binder):
    binder.bind(Config, to=provide_working_config, scope=inj.singleton)
    binder.bind(Metadata, to=provide_metadata, scope=request_scope)


INJECTOR = NamekoInjector(configure_bindings)


@INJECTOR.decorate_service
class Service:

    name = "test-service"

    @http("GET", "/config")
    def view_singleton_config(self, request, config: Config):
        return json.dumps({"feature_x": config.feature_x_enabled, "id": id(config)})

    @http("GET", "/worker/context/<int:id_>")
    def view_worker_context(self, request, id_, context: WorkerContext):
        return json.dumps(
            dict(service_name=context.service_name, call_id=context.call_id, id=id_)
        )

    @http("GET", "/injector/access")
    def check_injector_access(
        self, request, injector: inj.Injector, binder: inj.Binder
    ):
        # Injector can be accessed both from the service state and as a param.
        injector_from_nameko_injector_provider = self.injector  # type: ignore
        assert injector_from_nameko_injector_provider is injector
        # Same applies to binder.
        assert injector_from_nameko_injector_provider.binder is binder
        # This functionality is provided by the 'injector' library.
        return "ok"
