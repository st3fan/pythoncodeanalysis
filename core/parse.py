import ast
import copy
from core.scope import ModuleScope, FunctionScope, ScopeManager
from core.taint import Taint
from rules.base import Base
from rules.sanitizers import sanitizers
from rules.sinks import sinks, DecoratedReturnSink
from rules.sources import sources
from utils.astpp import dump


class Identifier(ast.NodeVisitor):
    """Identifies Sources, Sinks, and Sanitizers."""

    def __init__(self, *args, **kwargs):
        ast.NodeVisitor.__init__(self, *args, **kwargs)

        # request/route handlers
        self.handlers = {}

        # errors
        self.errors = []

        # initialize scope manager & module scope
        self.scope = ScopeManager(ModuleScope())

        # temporary solution (?)
        self.taint = self.scope

    @property
    def curscope(self):
        return self.scope.scopes[-1]

    def visit_Import(self, node):
        self.generic_visit(node)

        for alias in node.names:
            self.taint[alias.asname or alias.name] = alias.name

    def visit_ImportFrom(self, node):
        self.generic_visit(node)

        for alias in node.names:
            asname = alias.asname or alias.name
            taint = Taint(0)
            if not sources[node.module].attr(alias.name) is None:
                taint = sources[node.module].attr(alias.name)
            elif not sinks[node.module].attr(alias.name) is None:
                taint = sinks[node.module].attr(alias.name)
            elif not sanitizers[node.module].attr(alias.name) is None:
                taint = sanitizers[node.module].attr(alias.name)
            self.taint[asname] = taint

    def visit_FunctionDef(self, node):
        scope = self.scope.push(FunctionScope(node.name))
        scope.request_handler = None

        # TODO support multiple decorators
        if len(node.decorator_list) == 1 and \
                isinstance(node.decorator_list[0], ast.Call) and \
                isinstance(self.taint[node.decorator_list[0].func.id],
                           DecoratedReturnSink):
            uri = node.decorator_list[0].args[0].s

            # TODO support multiple keyword arguments
            kw = node.decorator_list[0].keywords
            if len(kw) == 1 and kw[0].arg == 'method' and \
                    isinstance(kw[0].value, ast.Str):
                method = kw[0].value.s
            else:
                method = 'GET'

            self.handlers[method, uri] = node

            # also keep some metadata for the FunctionScope
            scope.request_handler = method, uri

            # assign the sink taint
            node.sink = self.taint[node.decorator_list[0].func.id]

        self.generic_visit(node)
        self.scope.pop()

    def visit_Str(self, node):
        self.generic_visit(node)
        node.taint = Taint()

    def visit_Num(self, node):
        self.generic_visit(node)
        node.taint = Taint()

    def visit_Name(self, node):
        self.generic_visit(node)
        if not isinstance(node.ctx, ast.Store):
            node.taint = self.taint.get(node.id, Taint())
        else:
            node.taint = Taint()

    def visit_Attribute(self, node):
        self.generic_visit(node)

        node.taint = node.value.taint.attr(node.attr)

    def visit_BinOp(self, node):
        self.generic_visit(node)

        # 'fmt' % args
        if isinstance(node.op, ast.Mod) and isinstance(node.left, ast.Str):
            # 'fmt' % arg
            if isinstance(node.right, (ast.Name, ast.Attribute, ast.Call)):
                node.taint = node.right.taint
            # 'fmt' % (args,)
            elif isinstance(node.right, ast.Tuple):
                taint = Taint()
                for el in node.right.elts:
                    taint.update(el.taint)
                node.taint = taint
        # str + variable or variable + str
        elif isinstance(node.op, ast.Add):
            node.taint = node.left.taint | node.right.taint

    def visit_Assign(self, node):
        self.generic_visit(node)

        # single assignment
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            self.taint[node.targets[0].id] = node.value.taint
        # multiple assignments, but with equal count on both sides
        elif len(node.targets) == 1 and \
                isinstance(node.targets[0], ast.Tuple) and \
                isinstance(node.value, ast.Tuple) and \
                len(node.targets[0].elts) == len(node.value.elts):
            # TODO transaction kind of updating the taint
            for x in xrange(len(node.value.elts)):
                self.taint[node.targets[0].elts[x].id] = \
                    node.value.elts[x].taint

    def visit_Call(self, node):
        self.generic_visit(node)

        # check for simple sanitizers (which operate on one parameter only)
        if len(node.args) == 1:
            # we strip certain taints when it is in fact a simple sanitizer
            if not node.starargs and not node.kwargs:
                node.taint = node.func.taint.call(*node.args)
            else:
                node.taint = node.args[0].taint

    def visit_Return(self, node):
        self.generic_visit(node)

        # check against the DecoratedReturnSink
        if isinstance(self.curscope, FunctionScope) and \
                not self.curscope.request_handler is None:

            # get the taint for this function
            fnnode = self.handlers.get(self.curscope.request_handler, 0)
            source = sink = 0

            # get the source taint
            if hasattr(node.value, 'taint'):
                source = node.value.taint

            # get the sink taint
            sink = getattr(fnnode, 'sink', Taint())

            if source & sink:
                self.errors.append('Taint fail (%s) found at %d' %
                                   (Base.taint_str(source & sink),
                                    node.lineno))

    def visit_If(self, node):
        # handle the comparison under our normal scope
        self.visit(node.test)

        origscope = self.scope
        thenscope = copy.deepcopy(self.scope)
        elsescope = copy.deepcopy(self.scope)

        # handle the then body
        self.scope = self.taint = thenscope
        for x in node.body:
            self.visit(x)

        # handle the else body
        self.scope = self.taint = elsescope
        for x in node.orelse:
            self.visit(x)

        # conservative tainting for now
        origscope.merge(thenscope)
        origscope.merge(elsescope)

        # restore the scope
        self.scope = self.taint = origscope

    def visit_For(self, node):
        # handle the iterator in our normal scope
        self.generic_visit(node.iter)

        origscope = self.scope
        bodyscope = copy.deepcopy(self.scope)
        elsescope = copy.deepcopy(self.scope)

        # handle the body
        self.scope = self.taint = bodyscope
        for x in node.body:
            self.visit(x)

        # handle the else body
        self.scope = self.taint = elsescope
        for x in node.orelse:
            self.visit(x)

        # conservative tainting for now
        origscope.merge(bodyscope)
        origscope.merge(elsescope)

        # restore the scope
        self.scope = self.taint = origscope


def parse(fname):
    node = ast.parse(open(fname, 'rb').read())
    return node

if __name__ == '__main__':
    import sys
    print dump(parse(sys.argv[1]))
