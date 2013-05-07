import sys


class Taint(object):
    """Base class for tainted objects."""
    def __init__(self, taint_level=0):
        self.taint_level = taint_level

    def update(self, other):
        if isinstance(other, (int, long)):
            self.taint_level |= other
        elif isinstance(other, Taint):
            self.taint_level |= other.taint_level
        else:
            raise Exception('Invalid Taint update object')

    def __repr__(self):
        return '<%s: %d>' % (self.__class__.__name__, self.taint_level)

    def __nonzero__(self):
        return bool(self.taint_level)

    def __and__(self, other):
        return Taint(self.taint_level & other)

    def __rand__(self, other):
        return Taint(self.taint_level & other)

    def __or__(self, other):
        ret = Taint(self.taint_level)
        ret.update(other)
        return ret

    def __invert__(self):
        return Taint(~self.taint_level)

    def attr(self, attrname, default=None):
        raise Exception('attr has to be implemented by a subclass')


class AttributeTaint(Taint):
    """Taint object with support for attributes."""
    def __init__(self, taint_level=0):
        Taint.__init__(self, taint_level)
        self.attrs = {}

    def attr(self, attrname, default=None):
        if not attrname in self.attrs:
            print>>sys.stderr, 'attr', attrname, 'not defined for',
            print>>sys.stderr, self.__class__.__name__, '!'
            return default
        return self.attrs[attrname]

    def __setitem__(self, attrname, value):
        self.attrs[attrname] = value


class ConstAttributeTaint(Taint):
    """One taint for all attributes."""
    def attr(self, attrname, default=None):
        return Taint(self.taint_level)


class CallableTaint(Taint):
    """Callable functions returning a taint based on the input."""
    def call(self, *args, **kwargs):
        return Taint(self.taint_level)
