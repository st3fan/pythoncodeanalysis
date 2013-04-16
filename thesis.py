from core.parse import parse, Identifier
from utils.astpp import dump
import sys

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print 'Usage: python %s <website.py>' % sys.argv[0]
        exit(1)

    root = parse(sys.argv[1])
    x = Identifier()
    x.visit(root)
    print x.errors, x.taint, x.handlers
    print dump(root)
