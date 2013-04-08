import ast
from utils import astpp
import sys

if __name__ == '__main__':
    fd = open(sys.argv[1], 'rb') if len(sys.argv) != 1 else sys.stdin
    print astpp.dump(ast.parse(fd.read()))
