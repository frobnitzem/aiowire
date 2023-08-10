from typing import Optional, Dict, Union

try:
    import zmq
    import zmq.asyncio 
    Socket = Union[zmq.Socket, int]
    zmqPOLLIN = zmq.POLLIN
except ImportError:
    zmq = None # type: ignore[assignment]
    Socket = int # type: ignore[misc]
    zmqPOLLIN = 101

from .wire import Wire
from .event_loop import EventLoop

class Poller(Wire):
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
    def __init__(self, socks : Dict[Socket, Wire],
                       default_flags = zmqPOLLIN,
                       interval : Optional[int] = 1000):
        self.socks : Dict[Socket, Wire] = {}
        self.default_flags = default_flags
        self.interval = interval
        self.done = False

        self.poller = zmq.asyncio.Poller()
        for sock, cb in socks.items():
            self.register(sock, cb)

    def register(self, sock : Socket, cb : Wire, flags = None) -> None:
        """
        Add a listener on sock, invoking cb on activity.
        See pyzmq.Poller.register for more info on sock.

        If flags is None, self.default_flags is used.
        """
        if flags is None:
            flags = self.default_flags
        if sock in self.socks:
            raise IndexError(f"Already have a callback for sock: {sock}")
        self.poller.register(sock, flags)
        self.socks[sock] = cb

    def unregister(self, sock : Socket) -> None:
        self.poller.unregister(sock)
        del self.socks[sock]

    def shutdown(self) -> None:
        """
        Shutdown only needs to be called if the EventLoop
        is running in non-stop mode.
        """
        self.done = True
    
    async def __call__(self, ev : EventLoop) -> Optional[Wire]:
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
        return self
