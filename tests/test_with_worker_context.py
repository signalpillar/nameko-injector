"""Test accessing providers that depend on nameko's WorkerContext."""


import typing as t
import uuid

import injector as inj
import pytest
from nameko.containers import WorkerContext
from nameko_injector.core import NamekoInjector, request_scope

# WorkerContext takes a central place in the nameko DependencyProvider interface and
# many injector providers will depend on it for that reason.
# The module tests one of the scenarios for the demonstration purpose.


def test_debug_id_created(injector_in_test):
    debug_id = injector_in_test.get(DebugID)
    assert isinstance(debug_id, DebugID)
    assert debug_id.value.bytes


class DebugID(t.NamedTuple):
    value: uuid.UUID


@inj.provider
def provide_debug_id(worker_ctx: WorkerContext) -> DebugID:
    return DebugID(value=uuid.UUID(worker_ctx.call_id))


INJECTOR = NamekoInjector(
    lambda binder: binder.bind(DebugID, to=provide_debug_id, scope=request_scope)
)


@INJECTOR.decorate_service
class Service:
    name = "test"


@pytest.fixture
def service_class():
    return Service
