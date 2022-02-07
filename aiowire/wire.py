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
    def __rshift__(a, b): # >>
        return Sequence(a, b)
    def __ge__(a, b): # >=
        return ApplyM(a, b)
    def __mul__(a, n : int):
        return Repeat(a, n)
    async def __call__(self, ev, *args): # -> Optional[Wire]:
        return await self._aiowire(ev, *args)

class Sequence(Wire):
    """
    This Wire codifies the pattern, "call a, then b".
    It prevents us from having to write it for each kind of wire.
    Instead, we just create a Sequence wire.

    Any return value from `a` is ignored, so `b` is always
    called as b(ev).

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

class ApplyM(Wire):
    """
    This Wire codifies the pattern, "call a(ev), then b(ev, *ret)",
    where ret are the extra return values from a.

    It prevents us from having to write it for each kind of wire.
    Instead, we just create an ApplyM wire.

    Any return values from `a` are passed as
    function inputs to `b`.  For example, if a = Call(fn, x, y),
    and fn(x, y) returns ret, then `a` will return (None, ret),
    and `b` will be called as b(ev, *ret).

    Note:

    If `a` returns a tuple with a wire and a result, `(w, x)`,
    then both w(ev, *x) and b(ev, *x) will be run concurrently.

    Error-note:

    This kind of wire can lead to difficult-to-diagnose errors.
    If `a` returns something other than
       None | Callable | (Callable, List),
    then get_args will throw an error, and you'll have to find
    the wire `a` and fix its return type.
    """
    def __init__(self, a, b):
        self.a = a
        self.b = b
    async def __call__(self, ev, *args):
        ret = await self.a(ev, *args)
        if ret is not None:
            args = ev.start( ret ) # !!! See Error-note on ApplyM !!!
        else:
            args = []
        return self.b, args

class Call(Wire):
    """
    Convenience wire to call a function or coroutine with the given args.

    The return value of the wire created is (None, fix(ret)),
    where ret = [optionally await] fn(*args, **kwargs),
    and fix(ret) =
          ret if ret is a list/tuple
          [] if ret is None
          [ret] otherwise
    This way the return value of the function is always cast to a
    list of arguments that can be passed to the next Wire in a
    sequence.

    If there are call arguments "coming from a previous wire",
    they are ignored.

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
        if ret is None:
            return None
        if not isinstance(ret, (list,tuple)):
            ret = [ret]
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
