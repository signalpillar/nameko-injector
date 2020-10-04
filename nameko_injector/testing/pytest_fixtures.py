import uuid
from unittest import mock
import injector as inj

import pytest
from nameko.containers import WorkerContext
from nameko.testing.services import replace_dependencies
from nameko.testing.utils import get_container

from ..core import NamekoInjectorProvider


@pytest.fixture
def worker_ctx(service_class):
    # Redefine this fixture in your tests
    mocked_ctx = mock.Mock(spec=WorkerContext)
    mocked_ctx.args = []
    mocked_ctx.service_name = service_class.name
    mocked_ctx.call_id = str(uuid.uuid4())
    return mocked_ctx


@pytest.fixture
def injector_in_test(service_class, worker_ctx):
    provider = service_class.injector
    if not isinstance(provider, NamekoInjectorProvider):
        raise ValueError(
            "Injector-in-test cannot be created "
            f"if the service class {service_class} in test "
            "is not decorated with nameko-injector"
        )
    injector = provider.injector.create_child_injector(provider.injector._modules)
    injector.binder.bind(WorkerContext, to=inj.InstanceProvider(worker_ctx))
    return injector


@pytest.fixture
def service_class():
    raise NotImplementedError(
        'Redefine fixture "service_class" to return class of the service '
        "under the test. Usually it is a class of the service that is tested."
    )


@pytest.fixture
def container_overridden_dependencies(injector_in_test):
    """Return provider name to a new value to be set on the container."""
    # setting injector to injector_in_test is needed in 99% of the tests
    return {"injector": injector_in_test}


@pytest.fixture
def web_service(
    service_class, container_overridden_dependencies, runner_factory, web_config
):
    """Start service ready to serve HTTP requests."""
    runner = runner_factory(web_config, service_class)
    container = get_container(runner, service_class)
    replace_dependencies(container, **container_overridden_dependencies)
    runner.start()
    yield
    runner.stop()
