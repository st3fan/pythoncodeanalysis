from rules.base import Base


class Sink(Base):
    """Base class for all Sinks."""


class DecoratedReturnSink(Sink):
    """Sink for Decorated functions which return a value."""
    def __init__(self, framework, version, decorator, issink, affects):
        Sink.__init__(self, framework, version)
        self.decorator = decorator
        self.issink = issink
        self.affects = affects


def is_function_sink(name):
    for sink in sinks:
        if name == sink.decorator and sink.issink(name, None):
            return sink.affects
    return 0


sinks = [
    DecoratedReturnSink('bottle', None, 'bottle.route',
                        lambda x, ctx: True, Sink.XSS),
]
