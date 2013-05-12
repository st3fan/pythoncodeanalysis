import ast
import sys


class Taint(object):
    """Base class for tainted objects."""
    def __init__(self, taint_level=0):
        if isinstance(taint_level, Taint):
            self.taint_level = taint_level.taint_level
        else:
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
        return Taint(self.taint_level & other.taint_level)

    def __or__(self, other):
        ret = Taint(self.taint_level)
        ret.update(other)
        return ret

    def __invert__(self):
        return Taint(~self.taint_level)

    def __cmp__(self, other):
        return self.taint_level != other.taint_level

    def attr(self, attrname, default=None):
        raise Exception('attr has to be implemented by a subclass')

    def call(self, *args, **kwargs):
        """Callable functions returning a zero taint."""
        return Taint(0)

    def lookup(self, index):
        raise Exception('lookup has to be implemented by a subclass')

    def store(self, index, value):
        raise Exception('store has to be implemented by a subclass')


class TaintList(object):
    """List of Taint objects - handles phi expressions."""
    def __init__(self, *taints):
        self.taints = []
        self.taint_level = 0
        for taint in taints:
            if isinstance(taint, TaintList):
                self.taints += taint.taints
                self.taint_level |= taint.taint_level
            elif isinstance(taint, list):
                self.taints += taint
                for t in taint:
                    self.taint_level |= t.taint_level
            else:
                self.taints.append(taint)
                self.taint_level |= taint.taint_level

        # filter out duplicate taints
        self.taints = list(set(self.taints))

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__,
                             ', '.join(repr(x) for x in self.taints))

    def __nonzero__(self):
        return any(self.taints)

    def __and__(self, other):
        ret = []
        for taint in self.taints:
            if taint & other:
                ret.append(taint & other)
        return TaintList(ret)


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


class DictionaryTaint(Taint):
    """Taint for dictionaries."""
    def __init__(self, keys, values):
        Taint.__init__(self, -1)

        self.const_taint = {}
        self.dynamic_taint = Taint(0)

        # have dynamic key-values been written to this dictionary?
        self.has_dynamic = False

        for x in xrange(len(keys)):
            # it's a constant key index
            if isinstance(keys[x], ast.Str):
                self.const_taint[keys[x].s] = values[x].taint

            # if it's a dynamic key, then we update the dynamic taint
            self.dynamic_taint |= values[x].taint

    def lookup(self, index):
        # TODO support slices
        if not isinstance(index, ast.Index):
            raise Exception('unhandled lookup class: %s' %
                            index.__class__.__name__)

        # if there's a string index, then taint is a combination of the
        # hardcoded key and the the dynamic taint, if set
        if isinstance(index.value, ast.Str):
            ret = self.const_taint.get(index.value.s, Taint())
            return ret | self.dynamic_taint if self.has_dynamic else ret

        if isinstance(index.value, (ast.Name, ast.Attribute)):
            return self.dynamic_taint

        raise Exception('unhandled index lookup class: %s' %
                        index.value.__class__.__name__)

    def store(self, index, value):
        # TODO support slices
        if not isinstance(index, ast.Index):
            raise Exception('unhandled lookup class: %s' %
                            index.__class__.__name__)

        # the index is a constant index
        if isinstance(index.value, ast.Str):
            self.const_taint[index.value.s] = value.taint
            return

        # the index is an attribute or name
        if isinstance(index.value, (ast.Name, ast.Attribute)):
            self.has_dynamic = True
            self.dynamic_taint |= value.taint
            return

        # we can't handle this at the moment
        raise Exception('unhandled index lookup class: %s' %
                        index.value.__class__.__name__)
