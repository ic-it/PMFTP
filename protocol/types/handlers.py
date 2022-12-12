from io import BytesIO
from dataclasses import dataclass
from typing import Callable
from ..types.conn_side import ConnSide


@dataclass
class Handlers:
    on_connect: Callable[[ConnSide], None] = lambda side: None
    on_message_recv: Callable[[ConnSide, bytes, bool], None] = lambda side, msg, is_correct: None
    on_message_send: Callable[[ConnSide, bytes, bool], None] = lambda side, msg, is_correct: None

    on_file_recv: Callable[[ConnSide, BytesIO, str, bool], None] = lambda side, file, is_correct: None
    on_file_send: Callable[[ConnSide, BytesIO, str, bool], None] = lambda side, file, is_correct: None
    on_disconnect: Callable[[ConnSide], None] = lambda side: None