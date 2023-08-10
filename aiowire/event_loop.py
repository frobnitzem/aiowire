from typing import Optional, Callable, List, Dict
from inspect import isawaitable
import asyncio

from .wire import Wire

Handler = Callable[['EventLoop', Exception], None]

class UnhandledException(Exception):
    pass

def default_handler(handler : Optional[Handler] = None) -> Handler:
    """ This default handler captures the traceback that lead to its creation.

        Any exception raised by the provided handler will
        be re-raised, with an extra note on where this
        default_handler was created (i.e. the original `EventLoop.start()`)..

        If handler is None, then this works as if handler was just
        `raise UnhandledException`.
    """
    def insulated_handler(ev : 'EventLoop', e : Exception):
        if handler is None:
            raise UnhandledException("Wire with no exception handler") from e
        else:
            try:
                handler(ev, e)
            except Exception as e2:
                raise e2 from e
    return insulated_handler

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

    Exception Handling:

    The ev.start() method can take a second parameter
    that is a callback where all exceptions are sent.
    When a task (or any of its subtasks) raise an exception,
    the callback is called with the exception as its argument.
    Note that if a task is cancelled, the
    exception type will be asyncio.CancelledError.
    Because each task either raises an exception,
    returns another wire, or returns None,
    the handler will only be called once by each start()-ed
    task (or not at all).
    """
    def __init__(self, timeout : Optional[float] = None):
        self.tasks : Dict[asyncio.Task, Handler] = {}
        self.timeout = timeout

    def start(self, w : Optional[Wire],
              handler : Optional[Handler] = None,
              capture_context : bool = True) -> None:
        """ Schedule the wire, `w`, for execution with
            the given exception handler.

            If capture_context is True, then exceptions raised
            during invocation of the handler will be wrapped with
            a traceback showing where start() was originally called.

            `capture_context` is set to False when running Wire-s returned
            by Wire-s so we don't trace the entire state history, only
            the original `start()` location.
        """
        if w is None:
            return None
        coro = w(self)
        if isawaitable(coro):
            #t = asyncio.ensure_future(coro)
            t : asyncio.Task = asyncio.create_task(coro) # type: ignore[arg-type]
            if handler is None or capture_context:
                self.tasks[t] = default_handler(handler)
            else:
                self.tasks[t] = handler
        return None

    async def run(self, timeout : Optional[float] = None) -> None:
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
                handler = self.tasks.pop(t)
                # Need to await t to get its return value,
                # then pass it to start again.
                try:
                    ret = await t
                    if isinstance(ret, Wire):
                        self.start(ret, handler, False)
                    elif ret is not None:
                        handler(self, TypeError(f"Wire returned {ret}"))
                except Exception as e:
                    handler(self, e)
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
        self.tasks.clear()
        return False # continue to raise any exception
