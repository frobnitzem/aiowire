aiowire - A simple event loop using asyncio
============================================

This package implements a ``EventLoop`` class
that manages concurrent coroutines.

It is based on the principles of functional
reactive programming and draws inspiration
from Haskell's `Control.Wire <https://hackage.haskell.org/package/netwire-4.0.7/docs/Control-Wire.html>`_ library.

In particular, every co-routine started by the
event loop is a ``Wire``.

``Wire``-s either return ``None``, indicating they're done,
or another ``Wire``.

An example helps explain the idea::

    from aiowire import EventLoop

    event = 0
    async def show_event(ev) \
            -> Optional[Callable[[EventLoop],Awaitable]]:
        print("Running...")
        event += 1
        await asyncio.sleep(event*0.15)
        print(f"Event {event}")
        if event < 5:
            return show_event

    async with EventLoop(timeout=1) as event:
        event.start(show_event)
        event.start(show_event)


We start up an event loop and drop in two wires.
Each runs, then returns the ``show_event`` function.
The event loop runs those functions next... and so on.

But this isn't functional programming.  The wires
have access to the event loop, and can start more
tasks.  Easy, right?


What can I do with it?
^^^^^^^^^^^^^^^^^^^^^^

What if you have a server that's spawning programs,
working with sockets, and managing timeouts?  Drop
in one wire for each program, one polling on socket I/O,
and another acting as a timer (as above).

The canonical task types are thus::

    asyncio.create_subprocess_exec # run a process

    asyncio.sleep # awake the loop after a given time lapse

    zmq.asyncio.Poller.poll # awake the loop after I/O on socket/file
    # Note: see aiowire.Poller for a nice interface.

Now your sockets can launch programs, and your program
results can start/stop sockets, and everyone can start
background tasks.


Poller?
^^^^^^^

The ``Poller`` class lets you schedule callbacks in response
to socket or file-descriptor activity.  Of course, the callbacks
are wires, and run concurrently.


Tell me more
^^^^^^^^^^^^

Yes, you *could* just send async functions taking one
argument to ``EventLoop.start``, but where's the fun in
writing closures everywhere?

To take it to the next level, aiowire comes with a
``Wire`` convenience class that lets you write ``Wire``-s expressively.
The following class extensions help you make Wire-s out of common 
programming idioms:

* Wire(w): acts like an identity over "async func(ev):" functions
* Repeat(w, n): repeat wire ``w`` n times in a row
* Call(fn): call fn, ignore the return, and exit

Consider, for example, printing 4 alarms separated by some time interval::

    from aiowire import EventLoop, Call

    prog = ( Call(asyncio.sleep, 0.1) >> Call(print, 'beep\a') ) * 4

    async with EventLoop() as ev:
        ev.start(prog)

References
==========

* https://pyzmq.readthedocs.io/en/latest/api/zmq.html#poller
* https://pythontic.com/modules/select/poll
* https://blog.tomecek.net/post/non-blocking-stdin-in-python/
