import io
import random

from io import BytesIO
from time import time
from typing import Type, TypeVar, Generator
from ..types.flags import Flags
from ..types.packets.base import Packet
from ..types.header import Header, HEADER_SIZE
from ..types.packets.send_part import SendPartPacket
from ..types.iteration_status import IterationStatus
from ..types.keychain import Keychain


_T = TypeVar("_T")

class SendTransfer:
    def __init__(self,
                 keychain: Keychain,
                 send_stram: BytesIO,
                 data_type: Flags
                 ) -> None:
        self.__last_recv_time = time()
        
        self.__timeout = 10
        self.__resend_timeout = 0.5
        self.__window: dict[SendPartPacket, int] = {}
        self.__window_size = 50
        self.__transfer_id = random.randint(0, 2**16)
        self.__keychain = keychain
        self.__data_type = data_type
        

        self.__send_stram = send_stram
        self.__send_stram.seek(0, io.SEEK_END)
        self.__data_len = self.__send_stram.tell()
        self.__send_stram.seek(0)

        self._get_parts_iter = self._get_parts()
        self._build_packet = NotImplemented
        self._send = NotImplemented
        self._done = False
        self._got_fin = False

    @property
    def transfer_id(self) -> int:
        return self.__transfer_id
    
    @property
    def done(self) -> bool:
        return self._done and not len(self.__window) or self._got_fin or (self.__last_recv_time + self.__timeout < time())
    
    @property
    def progress(self) -> float:
        return self.__send_stram.tell() / (self.__data_len or 1) * 100
    
    @property
    def window_fill(self) -> int:
        return len(self.__window)
    
    @property
    def data_type(self) -> Flags:
        return self.__data_type

    def _recv(self, packet: SendPartPacket) -> None:
        self.__last_recv_time = time()
        packet.decrypt()
        
        if packet.header.flags & Flags.ACK:
            for ack in map(lambda x: int.from_bytes(x, 'big'), packet.data.split(b':')):
                if not ack:
                    continue

                self.__window = {p: t for p, t in self.__window.items() if p.header.seq_number != ack}
            
            ack_packet: Packet = self._build_packet(Flags.ACK, ack_number=packet.header.seq_number)
            ack_packet.header.transfer_id = self.__transfer_id
            self._send(ack_packet)
        
        if packet.header.flags & Flags.FIN:
            self._got_fin = True
    
    def _get_parts(self) -> Generator[tuple[bytes, int], None, None]:
        self.__send_stram.seek(0)
        while True:
            position = self.__send_stram.tell()
            data = self.__send_stram.read(1024-HEADER_SIZE-100)

            if len(data) == 0:
                break
            yield data, position

    def _iterate(self) -> IterationStatus:
        if self.__window:
            oldes_packet, time_ = min(self.__window.items(), key=lambda x: x[1])
            if time_ + self.__resend_timeout < time():
                self._send(oldes_packet)
                self.__window[oldes_packet] = time()

                return IterationStatus.BUSY

        if len(self.__window) < self.__window_size and not self.done:
            try:
                data, position = next(self._get_parts_iter)
            except StopIteration:
                self._done = True
                return IterationStatus.SLEEP
            
            packet: SendPartPacket = self._build_packet(Flags.SEND | Flags.PART, packet_factory=SendPartPacket)
            packet.header.transfer_id = self.__transfer_id
            packet.insertion_point = position
            packet.data_part = data
            packet._public_key = self.__keychain.other_public_key
            packet.encrypt()
            self.__window[packet] = time()
            self._send(packet)
            return IterationStatus.BUSY

        if self.done:
            return IterationStatus.FINISHED
        
        if self.__last_recv_time + self.__timeout < time():
            return IterationStatus.FINISHED

        return IterationStatus.SLEEP
