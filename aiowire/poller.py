from typing import Optional, Dict, Any

import zmq
import zmq.asyncio 

class Poller:
    """
    File descriptor poller.  When a file it's watching
    gets input, it starts the corresponding callback (Wire).

    init takes a dictionary mapping sockets to Wire-s

    Interval is a report-back time (in milliseconds).
    It is only needed in the case that EventLoop is run without
    a timeout AND you have some other Wire that will call
    Poller.shutdown().

    See `the pyzmq docs <https://pyzmq.readthedocs.io/en/latest/api/zmq.html#polling>`_
    for more info.
    """
    def __init__(self, socks,
                       default_flags = zmq.POLLIN,
                       interval : Optional[int] = 1000):
        self.socks = {}
        self.default_flags = default_flags
        self.interval = interval
        self.done = False

        self.poller = zmq.asyncio.Poller()
        for sock, cb in socks.items():
            self.register(sock, cb)

    def register(self, sock, cb, flags = None):
        """
        Add a listener on sock, invoking ``Wire`` cb on activity.
        See pyzmq.Poller.register for more info on sock.

        If flags is None, self.default_flags is used.
        """
        if flags is None:
            flags = self.default_flags
        assert sock not in self.socks, f"Already have a callback for {sock}"
        self.poller.register(sock, flags)
        self.socks[sock] = cb

    def unregister(self, sock):
        self.poller.unregister(sock)
        del self.socks[sock]

    def shutdown(self):
        """
        Shutdown only needs to be called if the EventLoop
        is running in non-stop mode.
        """
        self.done = True
    
    async def poll(self, ev):
        # TODO: we could further capture the coroutine
        # here within self, then cancel it
        # during shutdown -- then await would probably throw something.
        events = await self.poller.poll(self.interval)
        if self.done:
            return None

        for fd, event in events:
            cb = self.socks.get(fd, None)
            if cb is not None:
                ev.start(cb)
