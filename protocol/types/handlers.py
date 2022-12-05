from dataclasses import dataclass
from typing import Callable
from ..types.conn_side import ConnSide


@dataclass
class Handlers:
    on_connect: Callable[[ConnSide], None] = lambda side: None
    on_message: Callable[[ConnSide, bytes], None] = lambda side, msg: None
    on_disconnect: Callable[[ConnSide], None] = lambda side: None