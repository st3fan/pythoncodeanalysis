import ast
from utils.astpp import dump


class Identifier(ast.NodeVisitor):
    """Identifies Sources, Sinks, and Sanitizers."""

    def __init__(self, *args, **kwargs):
        ast.NodeVisitor.__init__(self, *args, **kwargs)

        # global variables
        self.g = {}

        # request/route handlers
        self.handlers = {}

        # taint data
        self.taint = {}

        # current function
        self.curfunc = None

        # errors
        self.errors = []

    def visit_Import(self, node):
        self.generic_visit(node)
        for alias in node.names:
            self.g[alias.asname or alias.name] = alias.name

    def visit_ImportFrom(self, node):
        self.generic_visit(node)
        for alias in node.names:
            asname = alias.asname or alias.name
            self.g[asname] = node.module + '.' + alias.name

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if len(node.decorator_list) == 1 and \
                isinstance(node.decorator_list[0], ast.Call) and \
                node.decorator_list[0].func.id == 'route':
            self.handlers[node.decorator_list[0].args[0].s] = node

        self.curfunc = node.name

    def visit_Attribute(self, node):
        self.generic_visit(node)
        if isinstance(node.value, ast.Attribute) and \
                isinstance(node.value.value, ast.Name) and \
                node.value.attr == 'query' and \
                node.value.value.id == 'request':
            self.taint[node] = True

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.Mod) and \
                isinstance(node.left, ast.Str):
            if isinstance(node.right, ast.Attribute):
                self.taint[node] = self.taint[node.right]
            elif isinstance(node.right, ast.Tuple):
                for el in node.right.elts:
                    self.taint[node] = \
                        self.taint.get(node) or self.taint.get(el)

    def visit_Return(self, node):
        self.generic_visit(node)
        if self.taint[node.value]:
            self.errors.append('Taint fail found at %d' % node.lineno)


def parse(fname):
    node = ast.parse(open(fname, 'rb').read())
    return node

if __name__ == '__main__':
    import sys
    print dump(parse(sys.argv[1]))
