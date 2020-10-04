import eventlet
import injector as inj
import pytest

from . import dummy_service


@pytest.fixture
def service_class():
    return dummy_service.Service


@pytest.fixture(autouse=True)
def service(web_service):
    yield


def test_singleton_config_injected(web_session):
    # make 2 calls on the service to ensure we get the same instance of the
    # config.
    responses = [web_session.get("/config") for _ in range(2)]
    assert {200} == {r.status_code for r in responses}
    data = {r.json()["id"] for r in responses}
    assert 1 == len(data)


class TestRequestScopeInPureConfiguration:
    @pytest.fixture
    def container_overridden_dependencies(self):
        # we need a vanilla behaviour of the service without replacing test injector
        # etc therefore we redefine fixture to not override any providers on the
        # service.
        # Without this change service will use injector_in_test that has mocked
        # worker_ctx bound. Our test will not get unique worker contexts on each call.
        return {}

    def test_request_scoped_injected(self, web_session):
        threads = [
            eventlet.spawn(web_session.get, f"/worker/context/{id_}")
            for id_ in range(10)
        ]
        responses = [t.wait() for t in threads]
        assert {200} == {r.status_code for r in responses}
        all_call_ids = {r.json()["call_id"] for r in responses}
        assert 10 == len(all_call_ids)


class TestErrorRaisedDuringInjection:
    """Test behaviour of the entrypoint when dependency injection fails."""

    @pytest.fixture
    def injector_in_test(self, injector_in_test):
        # Override config binding on the service by specifying another one in
        # child injector that will be used on the service instance.
        injector_in_test.binder.bind(
            dummy_service.Config,
            to=dummy_service.provide_failing_config,
            scope=inj.singleton,
        )
        return injector_in_test

    def test_http(self, web_session):
        response = web_session.get("/config")
        assert 500 == response.status_code
        assert b"Error: ValueError: Failed to create config\n" == response.content


def test_injector_access(web_session):
    response = web_session.get("/injector/access")
    assert 200 == response.status_code
    assert b"ok" == response.content
