import pytest
import asyncio
import datetime

from aiowire import __version__
from aiowire import (
    EventLoop,
    Poller,
    Wire,
    Call,
    Repeat,
    Forever,
    UnhandledException,
)

# Wires with strange return values.
async def return_non_callable(ev, x):
    assert x == 'x'
    return x

async def return_non_list(ev, x):
    assert x == 'x'
    return Wire(return_non_callable, x)

@pytest.mark.asyncio
async def test_return_types():
    for wire in [return_non_callable,
                 return_non_list]:
        with pytest.raises(UnhandledException) as e:
            async with EventLoop() as ev:
                ev.start( Wire(wire, 'x') )

    assert True

@pytest.mark.asyncio
async def test_callbacks():
    def raises(E):
        def check(ev, e):
            assert isinstance(e, E)

    for wire, check in [
                (return_non_callable, raises(TypeError)),
                (return_non_list, raises(TypeError)),
                #(check1, check0), # returns of None are not forwarded
                #(return_non_callable2, check2),
                #(return_non_list, check2),
                #(return_non_list2, check2),
                ]:
        async with EventLoop() as ev:
            ev.start( Call(wire, None, 'x'), check )

@pytest.mark.asyncio
async def test_return_launch():
    arg0 = 'hello'
    arg1 = 'world'

    def check(*args):
        assert args[0] == arg0
        if len(args) == 1:
            return
        assert args[1] == arg1
        if len(args) > 2:
            assert args[2] == arg1

    n = 1
    async def launcher(eve, *args):
        nonlocal n
        check(*args)
        assert len(args) == n
        if n < 500:
            n += 1
            args = args + (arg1,)
        await asyncio.sleep(0.001)
        return Wire(launcher, *args)

    async with EventLoop(timeout=0.02) as event:
        event.start( Wire(launcher, arg0) )

async def callee(eve, *args):
    assert args == (1,2)
    await asyncio.sleep(0.01)
    return None

@pytest.mark.asyncio
async def test_repeat_call():
    async with EventLoop(timeout=0.2) as eve:
        eve.start( Repeat(Wire(callee,1,2), 2) )
        eve.start( Repeat(Wire(callee,1,2), 3) )

@pytest.mark.asyncio
async def test_forever_call():
    async with EventLoop(timeout=0.2) as eve:
        eve.start( Forever(Wire(callee,1,2)) )

@pytest.mark.asyncio
async def test_repeatM_call():
    async with EventLoop(timeout=0.2) as eve:
        eve.start( Repeat(Wire(callee,1,2), 20) )
        eve.start( Repeat(Wire(callee,1,2), 4) )

@pytest.mark.asyncio
async def test_foreverM_call():
    async with EventLoop(timeout=0.2) as eve:
        eve.start( Forever(Wire(callee, 1, 2)) )
