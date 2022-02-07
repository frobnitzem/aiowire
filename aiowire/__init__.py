import importlib.metadata

__version__ = importlib.metadata.version("aiowire")

from .event_loop import EventLoop
from .poller import Poller
from .wire import Wire, Sequence, ApplyM, Call, Repeat, Forever
