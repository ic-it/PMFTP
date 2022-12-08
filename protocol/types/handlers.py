from io import BytesIO
from dataclasses import dataclass
from typing import Callable
from ..types.conn_side import ConnSide


@dataclass
class Handlers:
    on_connect: Callable[[ConnSide], None] = lambda side: None
    on_message: Callable[[ConnSide, bytes, bool], None] = lambda side, msg, is_correct: None
    on_file: Callable[[ConnSide, BytesIO, str, bool], None] = lambda side, file, is_correct: None
    on_disconnect: Callable[[ConnSide], None] = lambda side: None