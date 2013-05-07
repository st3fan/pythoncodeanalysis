from rules.base import Base
from core.taint import Taint, AttributeTaint


class Sink(Base):
    """Base class for all Sinks."""


class DecoratedReturnSink(Taint, Sink):
    """Sink for Decorated functions which return a value."""
    def __init__(self, taint_level, framework=None, version=None):
        Taint.__init__(self, taint_level)
        Sink.__init__(self, framework, version)


class _BottleRules(AttributeTaint, Sink):
    def __init__(self):
        """Rules for the Bottle framework."""
        Sink.__init__(self, 'bottle', None)
        AttributeTaint.__init__(self, -1)
        self['route'] = DecoratedReturnSink(Sink.XSS)


sinks = {
    'bottle': _BottleRules(),
}
