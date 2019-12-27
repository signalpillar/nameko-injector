import typing as t
import pytest
import functools
import json
import eventlet
from eventlet import corolocal

from injector import Injector, Scope, singleton, Module
import injector as inj

from . import dummy_service

# request-scope developed first?
# provide nameko request-scope dependencies (worker context, request for HTTP)


@pytest.fixture
def service_class():
    return dummy_service.Service


@pytest.fixture(autouse=True)
def service(web_service):
    yield


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


class TestErrorRaisedDuringInjection:
    """Test behaviour of the entrypoint when dependency injection fails."""

    @pytest.fixture
    def injector_bindings(self):
        return {'metadata': dummy_service.FailingConfigModule()}

    def test_http(self, web_session):
        response = web_session.get('/config')
        assert 500 == response.status_code
        assert b'Error: ValueError: Failed to create config\n' == response.content
