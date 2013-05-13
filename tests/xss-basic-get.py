"""Basic XSS in the GET request.

curl -S http://localhost:8000/?xss=<script>alert(1)</script>

"""
from bottle import request, route, run
from bottle import html_escape


@route('/')
def root():
    """tainted with xss."""
    return '<p>%s</p>' % request.query.xss


@route('/2')
def root2():
    """tainted with xss."""
    return '<p>%s, %s</p>' % (request.query.xss1, request.query.xss2)


@route('/3')
def root3():
    """tainted with xss."""
    a = request.query.xss
    return '<p>%s</p>' % a


@route('/4')
def root4():
    """tainted with xss."""
    a = request.query.xss
    return '<p>%s</p>' % (a,)


@route('/5')
def root5():
    """tainted with xss."""
    return '<p>' + request.query.xss + '</p>'


@route('/6')
def root6():
    """tainted with xss."""
    a, b = request.query.xss1, request.query.xss2
    return '<p>%s, %s</p>' % (a, b)


@route('/7')
def root7():
    """html_escape untaints the xss taint, so not tainted."""
    return '<p>%s</p>' % html_escape(request.query.xss)


def root8():
    """not tainted, there's no @route decorator."""
    return '<p>%s</p>' % request.query.xss


@route('/9')
def root9():
    """tainted with xss."""
    a = '<pre>' + request.query.code + '</pre>'
    b = '<html><body>%s</body></html>' % a
    return b


@route('/10')
def root10():
    """tainted with xss."""
    a = request.query
    return a.xss


if __name__ == '__main__':
    run(port=8000)
