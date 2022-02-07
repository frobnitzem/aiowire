import importlib.metadata

__version__ = importlib.metadata.version("aiowire")

from .event_loop import EventLoop
from .poller import Poller
from .wire import Wire, Sequence, Call, Repeat, Forever
from .wire import ApplyM, RepeatM, ForeverM
