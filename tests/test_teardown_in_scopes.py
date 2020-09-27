"""Test resources can be closed in the end of the scope life-cycle."""
import json
from unittest import mock

import injector as inj
import pytest
from nameko.web.handlers import http
from nameko_injector.core import NamekoInjector, resource_request_scope


# Main test of the module. It's goal is to ensure that resource with
# 'resource_request_scope' scope is injected and in the end of request it's freed.
# Checking this fact is quite a challenge as with the setup here we cannot access
# - provider (copy of NamekoInjectorProvider is created by nameko), to read internal
#   state
# - injector_in_test as it's created for the request by provider which internal state is
#   not accessible. Fixture doesn't work as we disabled mocking of the provider. With
#   the mocking, life-cycle methods like 'worker_setup' or 'worker_teardown' are not
#   called.
# In the test a global state (DB_MODULE) will be used to access injected. Injected
# resources have 'spy' field (mock instance) that records calls to 'close' method.
def test_session_closed_after_request(web_service, web_session):
    # When
    response = web_session.get("/db/session")
    # Then
    assert 200 == response.status_code, str(response.content)
    session_details = response.json()
    # session that is expected to be injected in the HTTP handler
    session = DB_MODULE.fake_db_session
    assert session and session.engine is DB_MODULE.fake_db_engine
    # Check 'close' method is called once.
    session.spy.close.assert_called_once()

    # Ensure that session is exactly what we need and was injected in the method.
    assert id(session) == session_details.get("session_id")
    assert id(DB_MODULE.fake_db_engine) == session_details.get("engine_id")


def test_session_closed_even_if_another_resource_failed_closing(
    web_service, web_session
):
    # When
    response = web_session.get("/db/session/failing")
    # Then
    assert 200 == response.status_code, str(response.content)
    session_details = response.json()

    session = DB_MODULE.fake_db_session
    failing_session = DB_MODULE.failing_db_session
    assert session and failing_session

    assert id(session) == session_details.get("session_id")
    assert (
        id(DB_MODULE.fake_db_engine)
        == session_details.get("engine_id")
        == id(session.engine)
        == id(failing_session.engine)
    )

    session.spy.close.assert_called_once()
    assert not failing_session.spy.close.called


class Spy:
    def __init__(self, injected_with: inj.Injector):
        self.spy = mock.Mock()
        self.injected_with = injected_with

    def close(self):
        self.spy.close()


# FakeDBEngine and FakeDBSession are resources that will be used in the test in
# different scopes. They play role of those resources that SHOULD be closed in the end
# of the scope life-cycle.
class FakeDBEngine(Spy):
    """Engine is a singleton created once based on the configuration"""


class FakeDBSession(Spy):
    """Session is created per request and must be closed after usage."""

    def __init__(self, engine: FakeDBEngine, injected_with: inj.Injector) -> None:
        super().__init__(injected_with=injected_with)
        self.engine = engine


class FailingOnCloseDBSession(FakeDBSession):
    def close(self):
        raise RuntimeError("Something went wrong")


class DBModule(inj.Module):
    def __init__(self):
        # The fields are only for testing purpose as it's really hard to access injected
        # objects from the test itself using provider, injector_in_test or other way or
        # mocking.
        # It makes impossible to run the tests in parallel.
        self.fake_db_engine = None
        self.fake_db_session = None
        self.failing_db_session = None

    def configure(self, binder: inj.Binder) -> None:
        binder.bind(FakeDBEngine, to=self._provide_db_engine, scope=inj.singleton)
        binder.bind(
            FakeDBSession, to=self._provide_db_session, scope=resource_request_scope
        )
        binder.bind(
            FailingOnCloseDBSession,
            to=self._provide_failing_db_session,
            scope=resource_request_scope,
        )

    @inj.provider
    def _provide_db_engine(self, injector: inj.Injector) -> FakeDBEngine:
        self.fake_db_engine = FakeDBEngine(injected_with=injector)
        return self.fake_db_engine

    @inj.provider
    def _provide_failing_db_session(
        self, engine: FakeDBEngine, injector: inj.Injector
    ) -> FailingOnCloseDBSession:
        self.failing_db_session = FailingOnCloseDBSession(
            engine=engine, injected_with=injector
        )
        return self.failing_db_session

    @inj.provider
    def _provide_db_session(
        self, engine: FakeDBEngine, injector: inj.Injector
    ) -> FakeDBSession:
        self.fake_db_session = FakeDBSession(engine=engine, injected_with=injector)
        return self.fake_db_session


DB_MODULE = DBModule()


INJECTOR = NamekoInjector(DB_MODULE)


@INJECTOR.decorate_service
class Service:
    name = "service"

    @http("GET", "/db/session/failing")
    def view_db_failing_session_id(
        self,
        request,
        session: FakeDBSession,
        failing_db_session: FailingOnCloseDBSession,
        injector: inj.Injector,
    ):
        return json.dumps(
            dict(
                session_id=id(session),
                engine_id=id(session.engine),
                failing_db_session_id=id(failing_db_session),
            )
        )

    @http("GET", "/db/session")
    def view_db_session_id(self, request, session: FakeDBSession):
        return json.dumps(dict(session_id=id(session), engine_id=id(session.engine)))


@pytest.fixture
def service_class():
    return Service


@pytest.fixture
def container_overridden_dependencies():
    # Do not override NamekoInjectorProvider as it prevents calling of worker_* methods
    # on the provider.
    return {}
