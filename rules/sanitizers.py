from core.taint import AttributeTaint, CallableTaint, Taint
from rules.base import Base


class Sanitizer(Base):
    """Base Class for all Sanitizers."""


class SimpleSanitizer(CallableTaint, Sanitizer):
    """Class for defining simple sanitizers.

    A simple sanitizer takes source input and emits legitimate sink output.

    """
    def __init__(self, taint_level, framework=None, version=None):
        Sanitizer.__init__(self, framework, version)
        CallableTaint.__init__(self, taint_level)

    def call(self, arg):
        return Taint(arg.taint.taint_level & ~self.taint_level)


class _BottleRules(AttributeTaint, Sanitizer):
    def __init__(self):
        """Rules for the Bottle framework."""
        Sanitizer.__init__(self, 'bottle', None)
        AttributeTaint.__init__(self, -1)
        self['html_escape'] = SimpleSanitizer(Sanitizer.XSS)


sanitizers = {
    'bottle': _BottleRules(),
}
