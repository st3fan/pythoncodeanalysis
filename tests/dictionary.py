from bottle import request, route, run


@route('/')
def root():
    """key a is tainted."""
    d = {
        'a': request.query.value,
        'b': 'default value'
    }
    return d['a']


@route('/2')
def root2():
    """key b is not tainted."""
    d = {
        'a': request.query.value,
        'b': 'default value'
    }
    return d['b']


@route('/3')
def root3():
    """index can be a and a is tainted."""
    d = {
        'a': request.query.value,
        'b': 'default value'
    }
    return d[request.query.key]


@route('/4')
def root4():
    """b can be overwritten, so b is tainted."""
    d = {
        'a': request.query.value,
        'b': 'default value'
    }
    d[request.query.key1] = request.query.value1
    return d['b']


@route('/5')
def root5():
    """couldn't possibly not be tainted."""
    d = {
        'a': request.query.value,
        'b': 'default value'
    }
    d[request.query.key1] = request.query.value1
    return d[request.query.key]


@route('/6')
def root6():
    """after assigning key c, b is still not tainted."""
    d = {
        'a': request.query.value,
        'b': 'default value'
    }
    d['c'] = request.query.value1
    return d['b']


@route('/7')
def root7():
    """after assigning key c, c is tainted."""
    d = {
        'a': request.query.value,
        'b': 'default value'
    }
    d['c'] = request.query.value1
    return d['c']


if __name__ == '__main__':
    run(port=8000)
