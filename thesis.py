from core.parse import parse, Identifier
from utils.astpp import dump
import sys

if __name__ == '__main__':
    root = parse(sys.argv[1])
    x = Identifier()
    x.visit(root)
    print x.errors, x.taint
    print dump(root)
