import pytest
import asyncio
import datetime

from aiowire import __version__
from aiowire import EventLoop, Poller, Wire, Call

def test_version():
    assert isinstance(__version__, str)

@pytest.mark.asyncio
async def test_syntax():
    counter = 0
    def incr(x, y):
        nonlocal counter
        assert x == 'beep'
        assert y == '\a'
        counter += 1
    prog = ( Call(asyncio.sleep, 0.01) >> Call(incr, 'beep', '\a') ) * 4

    async with EventLoop() as ev:
        ev.start(prog)

    assert counter == 4

@pytest.mark.asyncio
async def test_Poller():
    import sys, os, fcntl, fcntl
    # ctx = zmq.asyncio.Context()

    fd, wfd = os.pipe() # use a pipe for testing
    # set nonblocking so reads will complete
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    fl = fcntl.fcntl(wfd, fcntl.F_GETFL)
    fcntl.fcntl(wfd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    chrs = 0
    async def read(ev):
        nonlocal chrs
        print("Calling read")
        data = b''
        try:
          while True:
            if fd == 0:
                l = sys.stdin.read(64).encode()
            else:
                l = os.read(fd, 64)
            data += l
            if len(l) < 64 or not l:
                break
        except BlockingIOError:
            pass # python still has issues
        #return data
        chrs += len(data)

    poller = Poller( {fd : read} )

    async def run_cmd(ev):
        await asyncio.sleep(0.01)
        proc = await asyncio.create_subprocess_exec('ls')
        stdout, stderr = await proc.communicate()
        assert proc.returncode == 0
        os.write(wfd, b"8 chars\n")

    async with EventLoop(timeout=0.5) as event:
        event.start(poller)
        event.start(CountDown("tick", 0.1, 100))
        event.start(run_cmd)
        event.start(CountDown("done", 0.475, 1))

    assert chrs > 7

def CountDown(name, dt, n):
    def show():
        print(f"{name}: {datetime.datetime.now()}")
    return (Call(asyncio.sleep, dt) >> Call(show))*n

@pytest.mark.asyncio
async def test_countdown():
    C1 = CountDown("start", 0.2, 2)
    C2 = CountDown("cancel", 0.1, 4)
    async with EventLoop(timeout=1.5) as event:
        event.start(C1)
        event.start(C2)

