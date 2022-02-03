import pytest
import asyncio
import datetime

from aiowire import __version__
from aiowire import EventLoop, FDPoller

def test_version():
    assert isinstance(__version__, str)

class CountDown:
    def __init__(self, name, dt, n):
        self.name = name
        self.dt = dt
        self.n = n

    async def tick(self, event):
        await asyncio.sleep(self.dt)
        print(f"{self.name}: {datetime.datetime.now()}")
        self.n -= 1
        if self.n <= 0:
            return None
        return self.tick

@pytest.mark.asyncio
async def test_FDPoller():
    import sys
    #ctx = zmq.asyncio.Context()
    poller = FDPoller(sys.stdin.fileno())

    async def after(t, cmd, *args):
        await asyncio.sleep(t)
        await runcmd(cmd, *args)

    async with EventLoop(timeout=5.0) as event:
        event.start(poller.poll(event))
        event.start(CountDown("tick", 1.0, 100).tick(event))
        event.start(after(2.0, 'ls', '/'))
        event.start(CountDown("done", 4.75, 1).tick(event))

@pytest.mark.asyncio
async def test_countdown():
    C1 = CountDown("start", 0.2, 2)
    C2 = CountDown("cancel", 0.1, 4)
    async with EventLoop(timeout=1.5) as event:
        event.start(C1.tick(event))
        event.start(C2.tick(event))

@pytest.mark.asyncio
async def test_closure():
    async def show_event(ev, dt=0.2, msg=""):
        print("Running...")
        await asyncio.sleep(dt)
        print(msg)
        if msg != "":
            return show_event

    async with EventLoop(timeout=1) as event:
        event.start( show_event(event, 0.2, "last msg.") )
        event.start( show_event(event, 0.1, "Ding!") )

