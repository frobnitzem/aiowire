import pytest
import asyncio
import datetime

from aiowire import __version__
from aiowire import EventLoop, Poller, Wire, Call, Forever

# Wires with strange return values.
async def return_three(ev, x):
    assert x == 'x'
    return None, [], 'x'

async def return_non_callable(ev, x):
    assert x == 'x'
    return x

async def return_non_callable2(ev, x):
    assert x == 'x'
    return 'x', []

async def return_non_list(ev, x):
    assert x == 'x'
    return return_non_callable, None

async def return_non_list2(ev, x):
    assert x == 'x'
    return None, 'y'

@pytest.mark.asyncio
async def test_return_types():
    for wire in [return_three,
                 return_non_callable,
                 return_non_callable2,
                 return_non_list,
                 return_non_list2]:
        with pytest.raises(ValueError) as e:
            async with EventLoop() as ev:
                ev.start( (wire, ('x',)) )

    assert True

@pytest.mark.asyncio
async def test_call_return():
    async def check0(ev, *ret):
        assert len(ret) == 0

    async def check1(ev, *ret):
        assert len(ret) == 1

    async def check2(ev, *ret):
        assert len(ret) == 2

    async def check3(ev, *ret):
        assert len(ret) == 3

    for wire, check in [
                (return_three, check3),
                (return_non_callable, check1),
                (check1, check0), # returns of None are not forwarded
                (return_non_callable2, check2),
                (return_non_list, check2),
                (return_non_list2, check2) ]:
        async with EventLoop() as ev:
            ev.start( Call(wire, None, 'x') >= check )

@pytest.mark.asyncio
async def test_return_launch():
    arg0 = 'hello'
    arg1 = 'world'

    async def launcher(eve, *args):
        assert len(args) >= 2
        assert args[0] == arg0
        assert args[1] == arg1
        if len(args) > 2:
            assert args[2] == arg1

    n = 1
    async def return_launcher(eve, *arg):
        nonlocal n
        assert len(arg) == n
        n += 1
        await asyncio.sleep(0.001)
        return launcher, arg + (arg1,)

    async with EventLoop(timeout=0.02) as event:
        event.start( (Forever(return_launcher), [arg0]) )
