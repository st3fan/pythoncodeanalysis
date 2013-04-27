import ast
from core.scope import ModuleScope, FunctionScope
from rules.base import Base
from rules.sanitizers import is_sanitizer
from rules.sinks import is_function_sink
from rules.sources import is_source
from utils.astpp import dump


class TaintEntry(object):
    def __init__(self, affects=0):
        self.affects = affects

    def update(self, other):
        if isinstance(other, (int, long)):
            self.affects |= other
        elif isinstance(other, TaintEntry):
            self.affects |= other.affects
        else:
            raise Exception('Invalid TaintEntry update object')

    def __repr__(self):
        return '<TaintEntry: %d>' % self.affects

    def __nonzero__(self):
        return bool(self.affects)

    def __and__(self, other):
        return TaintEntry(self.affects & other)

    def __rand__(self, other):
        return TaintEntry(self.affects & other)


class TaintList(object):
    def __init__(self, l):
        self.l = l

    def __getitem__(self, index):
        """Find this item in one of the frames."""
        # TODO self.field should point to the lowest NestedClass
        for x in xrange(self.l.__len__()):
            if index in self.l[-x].symbol_map:
                return self.l[-x].symbol_map[index]
        raise IndexError('key not found: %s' % index)

    def get(self, index, default=None):
        try:
            ret = self.__getitem__(index)
        except IndexError:
            return default
        return ret

    def __setitem__(self, index, value):
        # TODO self.field should point to the lowest ClassScope
        self.l[-1].symbol_map[index] = value


class Identifier(ast.NodeVisitor):
    """Identifies Sources, Sinks, and Sanitizers."""

    def __init__(self, *args, **kwargs):
        ast.NodeVisitor.__init__(self, *args, **kwargs)

        # request/route handlers
        self.handlers = {}

        # frames scope & initialize module frame
        self._frames = [ModuleScope()]

        # errors
        self.errors = []

        # overloaded taint member
        self.taint = TaintList(self.frames)

    @property
    def frames(self):
        return self._frames

    @frames.setter
    def set_frames(self, value):
        raise Exception('TODO - update self.taint as well')

    def name(self, node):
        """Return a string representation of various nodes."""
        if isinstance(node, ast.Attribute):
            return self.name(node.value) + '.' + node.attr
        elif isinstance(node, ast.Name):
            ret = self.taint.get(node.id, node.id)
            return node.id if isinstance(ret, TaintEntry) else ret
        raise Exception('TODO - add support for %s node' %
                        node.__class__.__name__)

    def visit_Import(self, node):
        self.generic_visit(node)

        for alias in node.names:
            self.taint[alias.asname or alias.name] = alias.name

    def visit_ImportFrom(self, node):
        self.generic_visit(node)

        for alias in node.names:
            asname = alias.asname or alias.name
            self.taint[asname] = node.module + '.' + alias.name

    def visit_FunctionDef(self, node):
        self.frames.append(FunctionScope(node.name))
        self.frames[-1].request_handler = None

        # TODO support multiple decorators
        if len(self.frames) == 2 and len(node.decorator_list) == 1 and \
                isinstance(node.decorator_list[0], ast.Call) and \
                node.decorator_list[0].func.id == 'route':
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
            self.frames[1].request_handler = method, uri

            # TODO less hax, moar dynamic
            node.sink = is_function_sink(self.taint['route'])

        self.generic_visit(node)
        self.frames.pop()

    def visit_Attribute(self, node):
        self.generic_visit(node)

        name = self.name(node)
        self.taint[name] = TaintEntry(affects=is_source(name))

    def visit_BinOp(self, node):
        self.generic_visit(node)

        # 'fmt' % args
        if isinstance(node.op, ast.Mod) and isinstance(node.left, ast.Str):
            # 'fmt' % arg
            if isinstance(node.right, (ast.Name, ast.Attribute)):
                node.taint = self.taint[self.name(node.right)]
            elif isinstance(node.right, ast.Call):
                node.taint = node.right.taint
            # 'fmt' % (args,)
            elif isinstance(node.right, ast.Tuple):
                node.taint = TaintEntry()
                for el in node.right.elts:
                    if hasattr(el, 'taint'):
                        node.taint.update(el.taint)
                    else:
                        try:
                            node.taint.update(self.taint[self.name(el)])
                        except Exception as e:
                            print 'exc', e

        # str + variable or variable + str
        elif isinstance(node.op, ast.Add):
            node.taint = TaintEntry()
            if isinstance(node.left, ast.Str) and \
                    isinstance(node.right, (ast.Name, ast.Attribute)):
                node.taint.update(self.taint[self.name(node.right)])
            elif isinstance(node.right, ast.Str) and \
                    isinstance(node.left, (ast.Name, ast.Attribute)):
                node.taint.update(self.taint[self.name(node.left)])
            if hasattr(node.left, 'taint'):
                node.taint.update(node.left.taint)
            if hasattr(node.right, 'taint'):
                node.taint.update(node.right.taint)

    def visit_Assign(self, node):
        self.generic_visit(node)

        # single assignment
        if len(node.targets) == 1 and \
                isinstance(node.targets[0], ast.Name) and \
                isinstance(node.value, (ast.Name, ast.Attribute)):
            srcname = self.name(node.value)
            dstname = self.name(node.targets[0])
            self.taint[dstname] = self.taint[srcname]
        # single assignment, but with .taint
        elif len(node.targets) == 1 and \
                isinstance(node.targets[0], ast.Name) and \
                isinstance(node.value, ast.BinOp):
            dstname = self.name(node.targets[0])
            self.taint[dstname] = getattr(node.value, 'taint', TaintEntry())
        # multiple assignments, but with equal count on both sides
        elif len(node.targets) == 1 and \
                isinstance(node.targets[0], ast.Tuple) and \
                isinstance(node.value, ast.Tuple) and \
                len(node.targets[0].elts) == len(node.value.elts):
            # TODO transaction kind of updating the taint
            for x in xrange(node.value.elts.__len__()):
                srcname = self.name(node.value.elts[x])
                dstname = self.name(node.targets[0].elts[x])
                self.taint[dstname] = self.taint[srcname]

    def visit_Call(self, node):
        self.generic_visit(node)

        # check for simple sanitizers (which operate on one parameter only)
        if len(node.args) == 1:
            # we strip certain taints when it is in fact a simple sanitizer
            if not node.starargs and not node.kwargs:
                stripped_taint = is_sanitizer(self.name(node.func))
            else:
                stripped_taint = 0

            if hasattr(node.args[0], 'taint'):
                node.taint = node.args[0].taint & ~stripped_taint
            else:
                try:
                    name = self.name(node.args[0])
                    node.taint = self.taint[name] & ~stripped_taint
                except Exception:
                    pass

    def visit_Return(self, node):
        self.generic_visit(node)

        # if the current frame is two, i.e., a function inside a module, then
        # we have to check against the DecoratedReturnSink
        if len(self.frames) == 2 and \
                isinstance(self.frames[1], FunctionScope) and \
                not self.frames[1].request_handler is None:

            # get the taint for this function
            fnnode = self.handlers.get(self.frames[1].request_handler, 0)
            source = sink = 0

            # get the source taint
            if hasattr(node.value, 'taint'):
                source = node.value.taint
            else:
                try:
                    source = self.taint[self.name(node.value)]
                except Exception:
                    pass

            # get the sink taint
            sink = getattr(fnnode, 'sink', TaintEntry())

            if source & sink:
                self.errors.append('Taint fail (%s) found at %d' %
                                   (Base.taint_str(source & sink),
                                    node.lineno))


def parse(fname):
    node = ast.parse(open(fname, 'rb').read())
    return node

if __name__ == '__main__':
    import sys
    print dump(parse(sys.argv[1]))
