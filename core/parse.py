import ast
from utils.astpp import dump
from rules.sources import is_source


class NestedFrame(object):
    def __init__(self):
        self.taint = {}


class NestedModule(NestedFrame):
    pass


class NestedClass(NestedFrame):
    pass


class NestedFunction(NestedFrame):
    def __init__(self, funcname):
        NestedFrame.__init__(self)
        self.funcname = funcname


class NestedLambda(NestedFrame):
    pass


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


class TaintList(object):
    def __init__(self, l):
        self.l = l

    def __getitem__(self, index):
        """Find this item in one of the frames."""
        for x in xrange(self.l.__len__()):
            if index in self.l[-x].taint:
                return self.l[-x].taint[index]
        raise IndexError('key not found: %s' % index)

    def get(self, index, default=None):
        try:
            ret = self.__getitem__(index)
        except IndexError:
            return default
        return ret

    def __setitem__(self, index, value):
        self.l[-1].taint[index] = value


class Identifier(ast.NodeVisitor):
    """Identifies Sources, Sinks, and Sanitizers."""

    def __init__(self, *args, **kwargs):
        ast.NodeVisitor.__init__(self, *args, **kwargs)

        # request/route handlers
        self.handlers = {}

        # nested frames & initialize module frame
        self._frames = [NestedModule()]

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
        self.frames.append(NestedFunction(node.name))

        if len(self.frames) == 1 and len(node.decorator_list) == 1 and \
                isinstance(node.decorator_list[0], ast.Call) and \
                node.decorator_list[0].func.id == 'route':
            uri = node.decorator_list[0].args[0].s

            kw = node.decorator_list[0].keywords
            if len(kw) == 1 and kw[0].arg == 'method' and \
                    isinstance(kw[0].value, ast.Str):
                method = kw[0].value.s
            else:
                method = 'GET'

            self.handlers[method, uri] = node

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

    def visit_Assign(self, node):
        self.generic_visit(node)

        # single assignment
        if len(node.targets) == 1 and \
                isinstance(node.targets[0], ast.Name) and \
                isinstance(node.value, (ast.Name, ast.Attribute)):
            srcname = self.name(node.value)
            dstname = self.name(node.targets[0])
            self.taint[dstname] = self.taint[srcname]
        # multiple assignments, but with equal count on both sides
        elif len(node.targets) == 1 and \
                isinstance(node.targets[0], ast.Tuple) and \
                isinstance(node.value, ast.Tuple) and \
                len(node.targets[0].elts) == len(node.value.elts):
            for x in xrange(node.value.elts.__len__()):
                srcname = self.name(node.value.elts[x])
                dstname = self.name(node.targets[0].elts[x])
                self.taint[dstname] = self.taint[srcname]

    def visit_Return(self, node):
        self.generic_visit(node)

        if hasattr(node.value, 'taint') and node.value.taint:
            self.errors.append('Taint fail (%s) found at %d' %
                               (node.value.taint, node.lineno))


def parse(fname):
    node = ast.parse(open(fname, 'rb').read())
    return node

if __name__ == '__main__':
    import sys
    print dump(parse(sys.argv[1]))
