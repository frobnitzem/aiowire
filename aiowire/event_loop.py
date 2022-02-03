from typing import Optional, Dict, Union, Callable, Awaitable
from inspect import isawaitable
import asyncio

import os, sys, fcntl

import zmq
import zmq.asyncio

class EventLoop:
    """
    Create a wire-driven event loop.

    This event loop manages a set of concurrent
    async tasks.

    New async tasks can be launched by calling
    `EventLoop.start`.

    The return values of these tasks must be either
    None, or else another `async function` which will
    be called with the current event loop as its argument.

    This way, an async function can be run repeatedly just
    by returning its own name.

    The intended use case is for a server that starts
    several network connections and subprocesses, and
    wants to perform task/connection management as
    part of some of the callbacks.

    The canonical task types are thus:

        asyncio.create_subprocess_exec - run a process
        asyncio.sleep - awake the loop after a given time lapse
        zmq.asyncio.Poller.poll - awake the loop after I/O on socket/file

    Example Usage::

        async def show_event(ev, dt=0.2, msg="") \
                    -> Optional[Callable[[EventLoop],Awaitable]]:
            print("Running...")
            await asyncio.sleep(dt)
            print(msg)
            if msg != "":
                return show_event

        async with EventLoop(timeout=1) as event:
            event.start(show_event(event, 0.2, "last msg."))
            event.start(show_event(event, 0.1, "Ding!"))
    """
    def __init__(self, timeout=None):
        self.tasks = set()
        self.timeout = timeout

    def start(self, coro : Awaitable):
        t = asyncio.ensure_future(coro)
        #t = asyncio.create_task(coro)
        self.tasks.add(t)

    async def run(self, timeout = None) -> None:
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
                ret = await t
                # Execute the task's callback
                if ret is not None:
                    coro = ret(self)
                    # check if the function actually returned a coroutine
                    if isawaitable(coro):
                        self.start(coro)
            t1 = loop.time()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        # (exc_type, exc, traceback) are *sys.exc_info()
        # or else None (on normal exit)
        if exc_type is None: # run the event loop (in case we forgot)
            await self.run(self.timeout)

        for t in self.tasks: #[max(self.cur-1,0):]:
            if not t.done():
                t.cancel()
        return False # continue to raise any exception

# spawn a subprocess and wait for it to complete
async def runcmd(prog, *args, ret=False, outfile=None) -> Union[int,bytes]:
    """
    Run the command as an async process, passing
    stdout and stderr through to the terminal.

    If ret is True, send stderr through, but capture stdout.
    Also ignores outfile.
    Check the program exit code,

    - if 0, return stdout as a string
    - if not, return the exit code

    If outfile is a string or Path, send stdout and stderr to it
    instead of the terminal.
    """
    stdout = None
    stderr = None
    if ret:
        stdout = asyncio.subprocess.PIPE
    if outfile:
        # TODO: consider https://pypi.org/project/aiofiles/
        f = open(outfile, 'ab')
        stdout = f
        stderr = f
    proc = await asyncio.create_subprocess_exec(
                    prog, *args,
                    stdout=stdout, stderr=stderr)
    stdout, stderr = await proc.communicate()
    # note stdout/stderr are binary
    if outfile:
        f.close()

    if ret and proc.returncode == 0:
        return stdout
    return proc.returncode

class FDPoller:
    """
    File descriptor poller that prints
    out all contents from files it is watching.
    """
    def __init__(self, *fds):
        self.done = False
        # set files to nonblocking so reads will complete
        for fd in fds:
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        self.poller = zmq.asyncio.Poller()
        for fd in fds:
            self.poller.register(fd, zmq.POLLIN)

    def shutdown(self):
        self.done = True
    
    # timeout is in milliseconds
    async def poll(self, ev, timeout : Optional[int] = 1000):
        events = await self.poller.poll(timeout)
        for fd, event in events:
            s = self.read(fd).decode('utf-8')
            print(f"fd {fd}: {s.upper()}")
        
        if not self.done:
            return self.poll

    def read(self, fd):
        data = b''
        while True:
            if fd == 0:
                l = sys.stdin.read(64).encode('utf-8')
            else:
                l = os.read(fd, 64)
            if not l:
                break
            data += l
        return data

