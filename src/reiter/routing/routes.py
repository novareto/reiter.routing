import re
import inspect
from http import HTTPStatus

import autoroutes
import dataclasses
from horseman.meta import APIView
from horseman.http import HTTPError
from horseman.util import view_methods


@dataclasses.dataclass
class Route:
    path: str
    method: str
    endpoint: callable
    params: dict = dataclasses.field(default_factory=dict)
    extras: dict = dataclasses.field(default_factory=dict)


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
            members = view_methods(inst)
            if isinstance(inst, APIView):
                for name, func in members:
                    yield name, func
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
