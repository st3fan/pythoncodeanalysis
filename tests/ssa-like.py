"""Basic examples showing conditional / SSA-like structures."""
from bottle import request, route, run
#from bottle import html_escape


@route('/')
def root():
    if request.query.key == 'secret':
        a = request.query.value
    else:
        a = 'default value'
    return a


@route('/2')
def root2():
    if request.query.key == 'secret':
        a = request.query.value1
    elif request.query.key == 'secret2':
        a = request.query.value2
    else:
        a = 'default value'
    return a


@route('/3')
def root3():
    """Root3 is *exactly* the same as root2 at AST level.

    If you don't take this docstring into account.. :)
    """
    if request.query.key == 'secret':
        a = request.query.value1
    else:
        if request.query.key == 'secret2':
            a = request.query.value2
        else:
            a = 'default value'
    return a


@route('/4')
def root4():
    a = 'default value'
    if request.query.key == 'secret':
        a = request.query.value1
    elif request.query.key == 'secret2':
        a = request.query.value2
    return a

if __name__ == '__main__':
    run(port=8000)
