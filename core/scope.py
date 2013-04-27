

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
