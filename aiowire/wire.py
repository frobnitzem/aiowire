from inspect import isawaitable

class Wire:
    """
    Convenience wrapper for a ``Wire`` type.

    You don't have to use this type, any async function
    taking a single argument (the EventLoop) works as a wire.

    This wrapper just provides nice syntax for composition-in-time::

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
    def __init__(self, a):
        self._aiowire = a
    def __rshift__(a, b):
        return ApplyM(a, b)
    def __mul__(a, n : int):
        return Repeat(a, n)
    async def __call__(self, ev, *args): # -> Optional[Wire]:
        return await self._aiowire(ev, *args)

class ApplyM(Wire):
    """
    This Wire codifies the pattern, "call a, then b".
    It prevents us from having to write it for each kind of wire.
    Instead, we just create an ApplyM wire.

    Any return values from `a` are passed as
    function inputs to `b`.  In particular,
    if `a` returns (None, ret), then
    `b` is called as b(ev, *ret).

    Note:

    If `a` returns a tuple with a wire and a result, `(w, x)`,
    then both w(ev, *x) and b(ev, *x) will be run concurrently.
    """
    def __init__(self, a, b):
        self.a = a
        self.b = b
    async def __call__(self, ev, *args):
        ret = await self.a(ev, *args)
        if ret is not None:
            args = ev.start( ret )
        else:
            args = []
        return self.b, args

class Call(Wire):
    """
    Convenience wire to call a function or coroutine with the given args.

    The return value of the wire created is (None, ret),
    where ret = [await] fn(*args, **kwargs)

    If there are call arguments "in the wire", they are ignored.

    If the function returns an awaitable, it will be awaited too.
    """
    def __init__(self, fn, *args, **kwargs):
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
    async def __call__(self, ev, *ignored):
        ret = self.fn(*self.args, **self.kwargs)
        if isawaitable(ret):
            ret = await ret
        return None, ret

class Repeat(Wire):
    def __init__(self, a, n : int):
        self.a = a
        self.n = n

    async def __call__(self, ev, *args):
        self.n -= 1
        if self.n >= 0:
            M = ApplyM(self.a, self)
            return await M(ev, args)
        return None, args

class Forever(Wire):
    def __init__(self, a):
        self.a = a
    async def __call__(self, ev, *args):
        M = ApplyM(self.a, self)
        return await M(ev, *args)
