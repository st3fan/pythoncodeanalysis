from rules.base import Base


class Source(Base):
    """Base class for all Sources."""
    GENERIC = Base.SQLI | Base.DB


class AttributeSource(Source):
    """Class for defining Attribute sources."""
    def __init__(self, framework, version, baseattr, issource, affects):
        Source.__init__(self, framework, version)
        self.baseattr = baseattr
        self.issource = issource
        self.affects = affects


def is_source(name):
    for src in sources:
        if name.startswith(src.baseattr) and src.issource(name, None):
            return src.affects
    return 0


sources = [
    AttributeSource('bottle', None, 'bottle.request.GET',
                    lambda x, ctx: True, Source.XSS | Source.GENERIC),
    AttributeSource('bottle', None, 'bottle.request.query',
                    lambda x, ctx: True, Source.XSS | Source.GENERIC),
    AttributeSource('bottle', None, 'bottle.request.POST',
                    lambda x, ctx: True, Source.GENERIC),
    AttributeSource('bottle', None, 'bottle.request.forms',
                    lambda x, ctx: True, Source.GENERIC),
    AttributeSource('bottle', None, 'bottle.request.params',
                    lambda x, ctx: True, Source.XSS | Source.GENERIC),
]
