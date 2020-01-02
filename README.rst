nameko-injector
===============

`injector <https://pypi.org/project/injector/>`_ based dependency injection
mechanism for the nameko services. Project is similar to `flask-injector <https://pypi.org/project/Flask-Injector/>`_.

Problem
-------

Nameko provides a dependency injection mechanism, built-in in the framework.
It works in many cases but there are limitations:

1. All the dependencies are injected regardless of whether they are used in the entry-point. For instance, all the dependencies will be injected for ``/health`` HTTP entry point.
2. Dependencies cannot depend on each other.
3. The scope is an implementation detail. Frequency of the dependency creation depends on the ``DependencyProvider`` implementation.

Solution
--------

The library provides an alternative dependency injection mechanism to the one
that is built-in in nameko. Several types of `request` scope can
be used out of the box without special injector module declarations.

- ``nameko_injector.core.ServiceConfig``
- ``from nameko.containers.ServiceContainer``
- ``from nameko.containers.WorkerContext``

An example:

.. code:: python

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


Development
-----------
`tox`

TODO
----

- testing: Add the tests for RPC entry points
- document testing with the library
