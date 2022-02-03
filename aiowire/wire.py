from inspect import isawaitable

class Wire:
    """
    Convenience wrapper for a ``Wire`` type.

    You don't have to use this type, any async function
    taking a single argument (the EventLoop) works as a wire.

    This wrapper just provides nice syntax for composition-in-time::

        a >> b (a triggers b)

    If a returns None, then b is run.
    If a returns another Wire, then both it *and* b are run
    concurrently.

    It also provides a syntax for repeating a Wire ``n`` times::

        a * 3

    Any wires returned by ``a`` are run concurrently.
    """
    def __init__(self, a, b=None):
        self.a = a
        self.b = b
    def __rshift__(a, b):
        return Wire(a, b)
    def __mul__(a, n : int):
        return Repeat(a, n)
    async def __call__(self, ev): # -> Optional[Wire]:
        ret = await self.a(ev)
        if ret is not None:
            ev.start(ret)
        if self.b is not None:
            return await self.b(ev)
        return None

class Call(Wire):
    """
    Convenience wire to call a function or coroutine with the given args
    and ignore the return value.

    If the function returns an awaitable, it will be awaited too.
    """
    def __init__(self, fn, *args):
        self.fn = fn
        self.args = args
    async def __call__(self, ev):
        ret = self.fn(*self.args)
        if isawaitable(ret):
            await ret
        return None

class Repeat(Wire):
    def __init__(self, a, n : int):
        self.a = a
        self.n = n

    async def __call__(self, ev):
        ret = await self.a(ev)
        if ret is not None:
            ev.start(ret)
        self.n -= 1
        if self.n <= 0:
            return None
        return self
