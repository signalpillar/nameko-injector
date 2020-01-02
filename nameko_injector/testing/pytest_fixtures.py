import pytest

from ..core import NamekoInjector


@pytest.fixture
def injector_bindings():
    """Mapping of the overriding bindings for service injector."""
    return dict()


@pytest.fixture
def injector_in_test(service_class, injector_bindings):
    return NamekoInjector(
        bindings=dict(service_class.__injector_bindings__, **injector_bindings)
    )


@pytest.fixture
def service_class():
    raise NotImplementedError(
        'Redefine fixture "service_class" to return class of the service '
        "under the test. Usually it is a class of the service that is tested."
    )


@pytest.fixture
def web_service(runner_factory, web_config, service_class, injector_in_test):
    """Start service ready to serve HTTP requests."""
    service_config = web_config
    service_class = injector_in_test.decorate_service(service_class)
    runner = runner_factory(service_config, service_class)
    runner.start()
    yield
    runner.stop()
