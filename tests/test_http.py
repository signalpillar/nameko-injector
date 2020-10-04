import json
import uuid
import typing as t

import injector as inj
import pytest
from nameko.web.handlers import http
from nameko_injector.core import (
    NamekoInjector,
    request_scope,
    MissingInRequestScopeError,
)
from werkzeug.wrappers import Request


def test_http_request_injected(web_session, web_service):
    """Test Request being used as a transient dependency."""
    # Given
    debug_id = str(uuid.uuid4())
    # When
    response = web_session.get(
        f"/request/injection/{_HEADER_NAME}", headers={_HEADER_NAME: debug_id}
    )
    # Then
    assert 200 == response.status_code
    assert {
        "header_name": "debug-id",
        "header_value": debug_id,
        "same_request": True,
    } == response.json()


def test_http_request_access_failed(injector_in_test):
    # HTTP request is already bound in the NamekoInjector with expectation that it's
    # already set in the scope. In this case it's not set without HTTP call and also we
    # call from a different coroutine.
    with pytest.raises(MissingInRequestScopeError):
        injector_in_test.get(Request)


_HEADER_NAME = "debug-id"


@pytest.fixture
def service_class():
    return ServiceUnderTesting


@pytest.fixture
def container_overridden_dependencies():
    # Override nothing in the runner so no mocked contexts are used, thus
    # injector_in_test is NOT used.
    return {}


class HeaderEntry(t.NamedTuple):
    """Name and value of a header from HTTP request."""

    injected: Request
    name: str
    value: t.Optional[str]


@inj.provider
def provide_header_entry(request: Request) -> HeaderEntry:
    return HeaderEntry(
        injected=request,
        name=_HEADER_NAME,
        value=request.headers.get(_HEADER_NAME),
    )


INJECTOR = NamekoInjector(
    lambda binder: binder.bind(
        HeaderEntry, to=provide_header_entry, scope=request_scope
    )
)


@INJECTOR.decorate_service
class ServiceUnderTesting:
    name = "test"

    @http("get", "/request/injection/<header_name>")
    def view_http_request_injection(
        self, request, header_name: str, entry: HeaderEntry
    ):
        return json.dumps(
            dict(
                header_name=entry.name,
                same_request=request is entry.injected,
                header_value=entry.value,
            )
        )
