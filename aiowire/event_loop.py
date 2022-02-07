from typing import Optional, Callable, Union, Awaitable, List, Any, Tuple
from inspect import isawaitable
import asyncio

class EventLoop:
    """
    Create a wire-driven event loop.

    This event loop manages a set of concurrent
    async tasks.

    New async tasks can be launched by calling
    `EventLoop.start`.

    The tasks must be async-functions which take the event-loop
    as its only parameter.

    The return values of these tasks must be either
    None, or else another `async function` which will
    be called with the current event loop as its argument.

    This way, an async function can be run repeatedly just
    by returning its own name.

    The intended use case is for a server that starts
    several network connections and subprocesses, and
    wants to perform task/connection management as
    part of some of the callbacks.
    """
    def __init__(self, timeout=None):
        self.tasks = set()
        self.timeout = timeout

    def start(self, ret) -> List[Any]:
        if ret is None:
            return []
        fn, args = get_args(ret)
        if fn is None:
            return args
        coro = fn(self, *args)
        if isawaitable(coro):
            #t = asyncio.ensure_future(coro)
            t = asyncio.create_task(coro)
            self.tasks.add(t)
        return args

    async def run(self, timeout = None) -> None:
        """
        Run the event loop.  Usually this is called
        automatically when the ``async with EventLoop ...``
        context ends.
        """
        loop = asyncio.get_running_loop()
        t0 = loop.time()
        t1 = t0
        if timeout is None:
            fin = None
        else:
            fin = t0+timeout
        while len(self.tasks) > 0 and (fin is None or t1 < fin):
            if fin is None:
                dt = None
            else:
                dt = fin - t1
            done, pending = await asyncio.wait(
                    self.tasks,
                    timeout = dt,
                    return_when = asyncio.FIRST_COMPLETED)
            for t in done:
                self.tasks.remove(t)
                # Need to await t to get its return value,
                # then pass it to start again.
                self.start(await t)
            t1 = loop.time()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        # (exc_type, exc, traceback) are *sys.exc_info()
        # or else None (on normal exit)
        if exc_type is None: # run the event loop here
            await self.run(self.timeout)

        for t in self.tasks: #[max(self.cur-1,0):]:
            if not t.done():
                t.cancel()
        self.tasks = set()
        return False # continue to raise any exception

def get_args( ret : Union[Callable, Tuple[Optional[Callable], List]] ) \
                -> (Optional[Callable], List):
    """
    Interpret mutiple different potential return types from a Wire.

    - Callable   ~> call ret(ev)
    - List/Tuple ~> call ret[0](ev, *ret[1])
    """
    if isinstance(ret, Callable):
        return ret, []
    if len(ret) != 2 or not (ret[0] is None \
                             or isinstance(ret[0], Callable)) \
                     or not isinstance(ret[1], (list,tuple)):
        raise ValueError("Invalid Wire return type: should be either `None`, `Wire`, or `(Wire, List)`")
    return ret[0], ret[1]
