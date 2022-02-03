# aiowire - A simple event loop using asyncio

This package implements an `EventLoop` class
that manages concurrent coroutines.

It is based on the principles of functional
reactive programming and draws inspiration
from Haskell's [Control.Wire](https://hackage.haskell.org/package/netwire-4.0.7/docs/Control-Wire.html) library.

In particular, every co-routine started by the
event loop is a `Wire`.

`Wire`-s either return `None`, indicating they're done,
or another `Wire`.

An example helps explain the idea:

```
from aiowire import EventLoop

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

```

We start up an event loop and drop in two wires.
Each runs, then returns the `show_event` function.
The event loop runs those functions next... and so on.

But this isn't functional programming.  The wires
have access to the event loop, and can start more
tasks.  Easy, right?

## What can I do with it?

What if you have a server that's spawning programs,
working with sockets, and managing timeouts?  Drop
in one wire for each program, one polling on socket I/O,
and another acting as a timer (as above).

Now your sockets can launch programs, and your program
results can start/stop sockets, and everyone can start
background tasks.
