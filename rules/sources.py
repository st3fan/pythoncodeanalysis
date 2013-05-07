from rules.base import Base
from core.taint import ConstAttributeTaint, AttributeTaint


class Source(Base):
    """Base class for all Sources."""


class _BottleRequest(AttributeTaint, Source):
    """Rules for bottle.request."""
    def __init__(self):
        Source.__init__(self, 'bottle.request', None)
        AttributeTaint.__init__(self, -1)
        self['GET'] = self['query'] = ConstAttributeTaint(Source.ALL)
        self['POST'] = self['forms'] = ConstAttributeTaint(Source.SQLI)
        self['params'] = ConstAttributeTaint(Source.ALL)


class _BottleRules(AttributeTaint, Source):
    """Rules for the Bottle framework."""
    def __init__(self):
        Source.__init__(self, 'bottle', None)
        AttributeTaint.__init__(self, -1)
        self['request'] = _BottleRequest()


sources = {
    'bottle': _BottleRules(),
}
