import injector
import json
import pytest
from nameko.web.handlers import http
from nameko_injector.core import request_scope, NamekoInjector


from .dummy_service import Config


class ConfigWrapper:
    def __init__(self, config: Config) -> None:
        self.config = config


@injector.provider
def provide_wrapped_config(config: Config) -> ConfigWrapper:
    return ConfigWrapper(config)


INJECTOR = NamekoInjector([])


@INJECTOR.decorate_service
class ConfigAbusingService:
    name = "test_service"

    @http("GET", "/config/obj/ids")
    def view_config_obj_ids(self, request, config: Config, wrapped: ConfigWrapper):
        return json.dumps(
            {"directly_injected": id(config), "second_injection": id(wrapped.config)}
        )


@pytest.fixture
def service_class():
    "Configure 'web_service' fixture to use a new 'ConfigAbusingService' class."
    return ConfigAbusingService


@pytest.fixture
def injector_in_test(injector_in_test):
    # Use callable provider to ensure that if request doesn't work we create a new
    # instance each time.
    def provide_a_new_config_instance():
        return Config(feature_x_enabled=True)

    # re-bind Config
    injector_in_test.binder.bind(
        Config,
        to=provide_a_new_config_instance,
        scope=request_scope,
    )
    injector_in_test.binder.bind(
        ConfigWrapper, to=provide_wrapped_config, scope=request_scope
    )
    return injector_in_test


def test_same_value_injected(injector_in_test):
    c1 = injector_in_test.get(Config)
    c2 = injector_in_test.get(Config)
    w1 = injector_in_test.get(ConfigWrapper)
    assert c1 is c2 and c2 is w1.config


def test_same_value_injected_in_http_entrypoint(web_session, web_service):
    """Test dependency bound in request scope will be created once in that scope."""
    # Regardless how many times we inject configuration to make HTTP endpoint work it
    # should be the same instance, created once.
    response = web_session.get("/config/obj/ids")
    assert 200 == response.status_code, str(response.content)
    body = response.json()
    assert body["directly_injected"] == body["second_injection"]
