from typing import Optional
from inspect import isawaitable

class Wire:
    """
    Convenience wrapper for a ``Wire`` type.

    Technically you don't have to use this type, any async function
    taking a single argument (the EventLoop) works as a wire.
    Practically, type-checking works better if you cast it to
    a Wire.

    This wrapper also provides nice syntax for composition-in-time::

        a >> b (a triggers b)

    If a returns None, then b is run.
    If a returns another Wire, c, then both c *and* b are run
    concurrently.

    It also provides a syntax for repeating a Wire ``n`` times::

        a * 3

    Any wires returned by ``a`` are run concurrently.

    Note: This class is very minimal, and can be extended by
          any other class.  The only rule for extension is that
          IF the extension implements either __init__ or __call__,
          then it MUST implement both __init__ and __call__.
    """
    def __init__(self, a, *args, **kwargs):
        self._aiowire = a
        self.args   = args
        self.kwargs = kwargs
    def __rshift__(a, b): # >>
        return Sequence(a, b)
    def __mul__(a, n : int):
        return Repeat(a, n)
    async def __call__(self, ev) -> Optional['Wire']:
        ret = self._aiowire(ev, *self.args, **self.kwargs)
        if isawaitable(ret):
            ret = await ret
        return ret

class Sequence(Wire):
    """
    This Wire codifies the pattern, "call a, then b".

    If a returns None, then b is run.
    If a returns another Wire, c, then both c *and* b are run
    concurrently.
    """
    def __init__(self, a, b):
        self.a = a
        self.b = b
    async def __call__(self, ev) -> Optional[Wire]:
        ret = await self.a(ev)
        if ret is not None:
            ev.start( ret )
        return self.b

class Call(Wire):
    """
    Convenience wire to call a function or coroutine with the given args.

    The return value of the wire created is always None.
    """
    def __init__(self, fn, *args, **kwargs):
        self._aiowire_fn = fn
        self.args = args
        self.kwargs = kwargs
    async def __call__(self, ev) -> Optional[Wire]:
        ret = self._aiowire_fn(*self.args, **self.kwargs)
        if isawaitable(ret):
            ret = await ret
        return None

class Repeat(Wire):
    def __init__(self, a : Wire, n : int):
        self.a = a
        self.n = n

    async def __call__(self, ev) -> Optional[Wire]:
        self.n -= 1
        if self.n == 0:
            return self.a
        elif self.n > 0:
            M = Sequence(self.a, self)
            return await M(ev)
        return None

class Forever(Wire):
    def __init__(self, a : Wire):
        self.a = a
    async def __call__(self, ev) -> Optional[Wire]:
        M = Sequence(self.a, self)
        return await M(ev)
