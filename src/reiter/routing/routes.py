import collections
import inspect
import re
from http import HTTPStatus

import autoroutes
from horseman.meta import APIView
from horseman.http import HTTPError
from horseman.util import view_methods


Route = collections.namedtuple('Route', [
    'path', 'method', 'endpoint', 'params', 'extras'])


class Routes(autoroutes.Routes):

    __slots__ = ('_registry')

    clean_path_pattern = re.compile(r":[^}]+(?=})")

    def __init__(self):
        super().__init__()
        self._registry = {}

    def url_for(self, name: str, **kwargs):
        try:
            path, _ = self._registry[name]
            # Raises a KeyError too if some param misses
            return path.format(**kwargs)
        except KeyError:
            raise ValueError(
                f"No route found with name {name} and params {kwargs}")

    @staticmethod
    def route_payload(view, methods: list=None):
        if inspect.isclass(view):
            inst = view()
            if isinstance(inst, APIView):
                assert methods is None
                members = view_methods(inst)
                for name, func in members:
                    yield name, func
            else:
                assert methods is not None
                for method in methods:
                    yield method, inst.__call__
        else:
            if methods is None:
                methods = ['GET']
            for method in methods:
                yield method, view

    def register(self, path: str, methods: list = None, **extras):
        def routing(view):
            name = extras.pop("name", view.__name__.lower())
            if name in self._registry:
                _, handler = self._registry[name]
                if handler != view:
                    ref = f"{handler.__module__}.{handler.__name__}"
                    raise ValueError(
                        f"Route with name {name} already exists: {ref}.")

            self._registry[name] = path, view
            for method, endpoint in self.route_payload(view, methods):
                payload = {
                    method: endpoint,
                    'extras': extras
                }
                self.add(path, **payload)
            return view
        return routing

    def match(self, method: str, path_info: str) -> Route:
        methods, params = super().match(path_info)
        if methods is None:
            return None
        endpoint = methods.get(method)
        if endpoint is None:
            raise HTTPError(HTTPStatus.METHOD_NOT_ALLOWED)

        return Route(
            path=path_info,
            method=method,
            endpoint=endpoint,
            params=params,
            extras=methods.get('extras', {})
        )
