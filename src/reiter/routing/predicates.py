import wrapt
from horseman.response import Response


class PredicateError(Response, Exception):
    pass


def content_types(mimetypes: set):

    def restrict_content_types(request):
        if not request.content_type.mimetype in mimetypes:
            raise PredicateError.create(
                406, body=('Cannot handle Content-Type: '
                           f'`{request.content_type.mimetype}`.'))

    return restrict_content_types


def with_predicates(*predicates):

    @wrapt.decorator
    def assert_predicates(wrapped, instance, args, kwargs):
        request = args[0]
        for predicate in predicates:
            try:
                predicate(request)
            except PredicateError as exc:
                return exc
        return wrapped(*args, **kwargs)

    return assert_predicates
