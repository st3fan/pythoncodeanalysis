from core.taint import TaintList


class Scope(object):
    """Base Class for various Scoping types and rules."""
    def __init__(self):
        self.symbol_map = {}


class ModuleScope(Scope):
    """Module Scope."""


class ClassScope(Scope):
    """Class Scope."""


class FunctionScope(Scope):
    """Function Scope."""
    def __init__(self, funcname):
        Scope.__init__(self)
        self.funcname = funcname


class LambdaScope(Scope):
    """Lambda Scope."""


class ScopeManager(object):
    """Manages the various scopes as a stack."""
    def __init__(self, scope):
        self.scopes = [scope]

    def lookup(self, symbol):
        """Returns the value for a given symbol."""
        # TODO instance variables starting with self.
        for x in xrange(len(self.scopes)):
            # we start with the last frame
            if symbol in self.scopes[-x].symbol_map:
                return self.scopes[-x].symbol_map[symbol]
        raise IndexError('Symbol not found: %s' % symbol)

    def assign(self, symbol, value):
        """Assign a value to a symbol."""
        # first we try to find an existing symbol with this name
        # if it exists, then we overwrite it
        for x in xrange(len(self.scopes)):
            # we start with the last frame
            if symbol in self.scopes[-x].symbol_map:
                self.scopes[-x].symbol_map[symbol] = value
                return

        # if there's no existing symbol with this name, then we assign
        # the value to the correct scope
        self.scopes[-1].symbol_map[symbol] = value

    def push(self, scope):
        """Push a Scope onto the stack."""
        self.scopes.append(scope)
        return scope

    def pop(self):
        """Pop a Scope from the stack."""
        return self.scopes.pop()

    def __getitem__(self, symbol):
        return self.lookup(symbol)

    def __setitem__(self, symbol, value):
        self.assign(symbol, value)

    def get(self, symbol, default=None):
        try:
            return self.lookup(symbol)
        except IndexError:
            return default

    def intersection(self, other):
        """Intersection between two scopes manager objects."""
        assert len(self.scopes) == len(other.scopes)
        s, o = self.scopes, other.scopes

        ret = []
        for x in xrange(len(self.scopes)):
            scope = []
            for k in s[x].symbol_map:
                if not k in o[x].symbol_map:
                    scope.append((k, s[x].symbol_map[k]))
                elif s[x].symbol_map[k] != o[x].symbol_map[k]:
                    scope.append((k, s[x].symbol_map[k]))
                    scope.append((k, o[x].symbol_map[k]))
            for k in (_ for _ in o[x].symbol_map if not _ in s[x].symbol_map):
                scope.append((k, o[x].symbol_map[k]))
            ret.append(scope)
        return ret

    def merge(self, other):
        """Merge the other scope into our scope."""
        inter = self.intersection(other)
        for x in xrange(len(inter)):
            for k, v in inter[x]:
                old = self.scopes[x].symbol_map.get(k, [])
                old = [old] if not isinstance(old, list) else old
                self.scopes[x].symbol_map[k] = TaintList(v, *old)
