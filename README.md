# nameko-injector

[injector](https://pypi.org/project/injector/ "cool injector library") based
dependency injection mechanism for the nameko services. Project is similar to [flask-injector](https://pypi.org/project/Flask-Injector/).

## Problem
Nameko provides dependency injection mechanism, built-in in the framework.
It works in many cases but there are limitations:

1. All the dependencies are injected regardless whether they are used in the
  entrypoint. For instance, all the dependencies will be injected for `/health`
  HTTP entry point.
2. Dependencies cannot depend on each other.
3. Scope is an implementation detail. Frequency of the dependency creation
  depends on the `DependencyProvider` implementation.

## Solution

The library provides an alternative dependency injection mechanism to the one
that is bult in in nameko. There are several types of `request` scope that can
be used out of the box without special injector modules declarations.

- `nameko_injector.core.ServiceConfig`
- `from nameko.containers.ServiceContainer`
- `from nameko.containers.WorkerContext`

An example:

```
import json
from nameko_injector.core import NamekoInjector, ServiceConfig
from nameko.web.handlers import http


INJECTOR = NamekoInjector()

@INJECTOR.decorate_service
class Service:

  name = 'service-name'

  @http('GET', '/health')
  def health(self, request):
     return {'status': 'ok'}

  @http('GET', '/config')
  def view_config(self, request, config: ServiceConfig):
     return json.dumps(config)
```

## Development

```
tox
```

## TODO

- testing: Add the tests for RPC entrypoints
