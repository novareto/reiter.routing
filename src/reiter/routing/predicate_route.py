from collections import defaultdict
from typing import Mapping, Callable, List, Tuple
from horseman.meta import Overhead
from horseman.response import Response
from horseman.prototyping import Environ
from reiter.routing.predicates import PredicateError


Predicates = List[Callable[[Overhead], Response]]
View = Callable[[Overhead, Environ], Response]


class PredicateRouting(type):

    def __init__(cls, name, bases, attrs):
        type.__init__(cls, name, bases, attrs)
        cls.views = None

    def __call__(cls, *args, **kwargs):
        if cls.views is None:
            cls.views = defaultdict(list)
        return type.__call__(cls, *args, **kwargs)


class BranchingView(metaclass=PredicateRouting):

    views: Mapping[str, List[Tuple[Predicates, View]]]

    def __call__(self, overhead: Overhead, **params) -> Response:
        if available_views := self.views.get(overhead.method):
            for predicates, view in available_views:
                for predicate in predicates:
                    try:
                        predicate(overhead)
                    except PredicateError:
                        break
                else:
                    return view(overhead, **params)

            return Response.create(406)

        # Method not allowed
        return Response.create(405)

    @classmethod
    def register(cls, methods: List, *predicates: Predicates):
        def register_view(view: View):
            for method in methods:
                method = method.upper()
                cls.views[method].append((predicates, view))
            return view
        return register_view
