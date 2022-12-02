import random

from typing import Generator
from .types.flags import Flags
from .types.header import Header
from .types.packets.base import Packet
from .types.packets.syn_send_msg import SynSendMsgPacket

class DataTransfer:
    def __init__(self) -> None:
        self._window_id = random.randint(0, 2**32)
        self._data = b''
        self._data_length = 0
        self._data_type = None
        self._max_data_size = 1024 - Header.HEADER_SIZE
        self._window: list[Packet] = []
        self._window_size = 0

    def fragments(self) -> Generator[bytes, None, None]:
        for i in range(0, len(self._data), self._max_data_size):
            yield self._data[i:i+self._max_data_size]
    
    def _init_receive(self, packet: Packet) -> None:
        if packet.header.flags & Flags.SYN & Flags.SEND & Flags.MSG:
            self._data_type = Flags.MSG
            msg_packet = packet.upcast(SynSendMsgPacket)

            self._window_id = msg_packet.header.window_id
            self._window_size = msg_packet.header.window_size
            self._data_length = msg_packet.message_len
        
    def _init_send(self, packet) -> None:
        if packet.header.flags & Flags.SYN & Flags.SEND & Flags.MSG:
            self._data_type = Flags.MSG
            msg_packet = packet.upcast(SynSendMsgPacket)
            self._window_size = msg_packet.header.window_size
            self._data_length = len(self._data)