import importlib.metadata

__version__ = importlib.metadata.version("aiowire")

from .event_loop import EventLoop, UnhandledException
from .poller import Poller
from .wire import (
    Wire,
    Sequence,
    Call,
    Repeat,
    Forever,
)
