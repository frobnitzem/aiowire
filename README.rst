aiowire - A simple event loop using asyncio
============================================

.. image:: https://github.com/frobnitzem/aiowire/actions/workflows/python-package.yml/badge.svg
   :target: https://github.com/frobnitzem/aiowire/actions
   :alt: CI
.. image:: https://codecov.io/github/frobnitzem/aiowire/branch/main/graph/badge.svg
   :target: https://app.codecov.io/gh/frobnitzem/aiowire
   :alt: Coverage

This package implements a ``EventLoop`` class
that manages concurrent coroutines.

It is based on the principles of functional
reactive programming and draws inspiration
from Haskell's `Control.Wire <https://hackage.haskell.org/package/netwire-4.0.7/docs/Control-Wire.html>`_ library.

In particular, every co-routine started by the event loop is a ``Wire``.

``Wire``-s either return ``None``, indicating they're done, or another
``Wire``.

An example helps explain the idea::

    from aiowire import EventLoop

    event = 0
    async def show_event(ev) -> Optional[Wire]:
        print("Running...")
        event += 1
        await asyncio.sleep(event*0.15)
        print(f"Event {event}")
        if event < 5:
            return Wire(show_event)
        return None

    async with EventLoop(timeout=1) as event:
        event.start(show_event)
        event.start(show_event)


We start up an event loop and drop in two wires.
Each runs, then returns the ``show_event`` function.
The event loop runs those functions next... and so on.

But since this isn't functional programming.  The wires
have access to the event loop, and can start more
tasks.  Easy, right?


What can I do with it?
^^^^^^^^^^^^^^^^^^^^^^

What if you have a server that's spawning programs,
working with sockets, and managing timeouts?  Drop
in one wire for each program, one polling on socket I/O,
and another acting as a timer (as above).

Some canonical task types that do these include::

    asyncio.create_subprocess_exec # run a program

    asyncio.sleep # awake the loop after a given time lapse

    zmq.asyncio.Poller.poll # awake the loop after I/O on socket/file

    aiowire.Poller # Wire-y interface to zmq.asyncio.Poller


Think about each wire as a finite state machine.
For example,

.. mermaid::

    flowchart LR
        R[Ready] --> N{New Task?};
        N -- Yes --> W[Working];
        W --> C{Complete?};
        C -- Yes --> R;

can be implemented like so::

    async def ready(ev : EventLoop, info : X) -> Optional[Wire]:
        if info.new_task():
            do_working_action()
            return Wire(working, info) # move to working state

        # Return a sequence of 2 wires:
        return Call(asyncio.sleep, 1.0) >> Wire(ready, info)

    async def working(ev : EventLoop, info : X) -> Wire:
        if info.complete():
            do_complete_action()
            return Wire(ready, info)
        await asyncio.sleep(0.5) # directly sleep a bit
        return Wire(working, info)

Note how your sockets can launch programs, and your program
results can start/stop sockets, and everyone can start
background tasks.


Poller?
^^^^^^^

The ``Poller`` class lets you schedule callbacks in response
to socket or file-descriptor activity.  Of course, the callbacks
are wires, and run concurrently.

Poller is also a Wire, created as,
`Poller(dictionary mapping sockets / fd-s to callback wires)`.

You add it to your event loop as usual::

    # ... create sock from zmq.asyncio.Context

    async def echo(ev):
        await sock.send( await sock.recv() )

    todo = { 0:  Call(print, "received input on sys.stdin"),
             sock: Wire(echo)
           }
    async with EventLoop() as ev:
        ev.start( Poller(todo) )


Tell me more
^^^^^^^^^^^^

Yes, you *could* just send async functions taking one
argument to ``EventLoop.start``, but where's the fun in
writing closures everywhere?

To take it to the next level, aiowire comes with a
``Wire`` convenience class that lets you write ``Wire``-s expressively.
The following class extensions help you make Wire-s out of common 
programming idioms:

* `Wire(w)`: acts like an identity over "async func(ev):" functions
* `Repeat(w, n)`: repeat wire ``w`` n times in a row
* `Forever(w)`: repeat forever -- like `Repeat(w) * infinity`
* `Call(fn, *args, **kargs)`: call fn (normal or async),
  ignore the return, and exit

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
