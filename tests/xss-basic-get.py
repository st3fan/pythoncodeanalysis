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

if __name__ == '__main__':
    run(port=8000)
