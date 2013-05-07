

class Base:
    """Base class for all Rule Classes."""
    XSS, SQLI, DB = 1, 2, 4
    ALL = XSS | SQLI | DB

    def __init__(self, framework, version):
        self.framework = framework
        self.version = version

    @staticmethod
    def taint_str(index):
        ret = []
        if Base.XSS & index:
            ret.append('XSS')
        if Base.SQLI & index:
            ret.append('SQLI')
        if Base.DB & index:
            ret.append('DB')
        return ', '.join(ret)
