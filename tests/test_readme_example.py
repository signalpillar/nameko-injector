import json
import typing as t

import injector
import pytest
from nameko.containers import ServiceContainer
from nameko.web.handlers import http
from nameko_injector.core import NamekoInjector


class ServiceConfig:
    value: t.Mapping


@injector.provider
def provide_service_config(container: ServiceContainer) -> ServiceConfig:
    return container.config


def configure(binder):
    binder.bind(
        ServiceConfig,
        to=provide_service_config,
        scope=injector.singleton,
    )


INJECTOR = NamekoInjector(configure)


@INJECTOR.decorate_service
class Service:

    name = "service-name"

    @http("GET", "/config")
    def view_config(self, request, config: ServiceConfig):
        # 'config' is injected as singleton in each request that specifies it's type in
        # the view function's signature.
        return json.dumps(config)


# ======================== Testing part
@pytest.fixture
def service_class():
    return Service


@pytest.fixture
def container_overridden_dependencies():
    return {}


def test_view_config(web_service, web_session, web_config_port):
    response = web_session.get("/config")

    assert 200 == response.status_code
    assert {"WEB_SERVER_ADDRESS": f"127.0.0.1:{web_config_port}"} == response.json()
