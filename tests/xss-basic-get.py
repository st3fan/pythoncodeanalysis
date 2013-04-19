"""Basic XSS in the GET request.

curl -S http://localhost:8000/?xss=<script>alert(1)</script>

"""
from bottle import request, route, run


@route('/')
def root():
    return '<p>%s</p>' % request.query.xss


@route('/2')
def root2():
    return '<p>%s, %s</p>' % (request.query.xss1, request.query.xss2)


@route('/3')
def root3():
    a = request.query.xss
    return '<p>%s</p>' % a


@route('/4')
def root4():
    a = request.query.xss
    return '<p>%s</p>' % (a,)


@route('/5')
def root5():
    return '<p>' + request.query.xss + '</p>'


@route('/6')
def root6():
    a, b = request.query.xss1, request.query.xss2
    return '<p>%s, %s</p>' % (a, b)

if __name__ == '__main__':
    run(port=8000)
