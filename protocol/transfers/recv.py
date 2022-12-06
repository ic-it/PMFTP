import logging

from io import BytesIO
from time import time
from typing import Type, TypeVar
from ..types.flags import Flags
from ..types.packets.base import Packet
from ..types.packets.send_part import SendPartPacket
from ..types.iteration_status import IterationStatus
from ..types.keychain import Keychain


LOG = logging.getLogger("RecvTransfer")
_T = TypeVar("_T")

class RecvTransfer:
    def __init__(self, 
                 length: int, 
                 transfer_id: int, 
                 keychain: Keychain,
                 recv_stram: BytesIO,
                 data_type: Flags,
                 filename: bytes = None) -> None:
        self.__last_recv_time = time()
        self.__last_process_time = time()

        self.__timeout = 50
        self.__ack_timeout = 0.5
        self.__process_window_timeout = 0.1

        self.__max_ack_size = 50

        self.__length = length
        self.__window: list[SendPartPacket] = []
        self.__processed_packets: list[int] = []
        self.__transfer_id = transfer_id
        self.__recv_stram = recv_stram
        self.__recived_data_length = 0
        self.__keychain = keychain
        self.__window_size = 10
        self._build_packet = NotImplemented
        self._send = NotImplemented
        self.__data_type = data_type
        self.__filename = filename

        self._acks: dict[SendPartPacket, int] = {}
    
    def _recv(self, packet: SendPartPacket) -> None:
        self.__last_recv_time = time()
        
        if packet.header.flags & Flags.ACK:
            self._acks = {p: t for p, t in self._acks.items() if p.header.seq_number != packet.header.ack_number}
            return
        
        self.__window.append(packet.decrypt())
    
    @property
    def done(self) -> bool:
        return self.__recived_data_length == self.__length and not len(self.__window) and not len(self._acks) or (self.__last_recv_time + self.__timeout < time())

    @property
    def data_type(self) -> Flags:
        return self.__data_type
    
    @property
    def filename(self) -> bytes | None:
        return self.__filename
    
    def _process_window(self) -> IterationStatus:
        if not len(self.__window):
            return IterationStatus.SLEEP
        sq_nums = []
        while len(sq_nums) < self.__max_ack_size and len(self.__window):
            packet = self.__window.pop()
            if packet.header.seq_number in self.__processed_packets:
                continue
            self.__recv_stram.seek(packet.insertion_point)
            self.__recv_stram.write(packet.data_part)
            self.__recived_data_length += len(packet.data_part)
            sq_nums.append(packet.header.seq_number)
            self.__processed_packets.append(packet.header.seq_number)
        
        ack_packet: Packet = self._build_packet(Flags.ACK)
        ack_packet.header.transfer_id = self.__transfer_id
        ack_packet.data = b':'.join(
            map(
                lambda x: x.to_bytes(4, 'big'),
                sq_nums
            )
        )

        ack_packet._public_key = self.__keychain.other_public_key
        ack_packet.encrypt()

        self._acks[ack_packet] = time()
        self._send(ack_packet)

        self.__last_process_time = time()

        return IterationStatus.BUSY


    def _iterate(self) -> IterationStatus:
        if len(self.__window) >= self.__window_size and self.__process_window_timeout + self.__last_process_time < time():
            return self._process_window()
        
        if len(self._acks):
            oldest_ack, time_ = min(self._acks.items(), key=lambda x: x[1])
            if time_ + self.__ack_timeout < time():
                self._send(oldest_ack)
                self._acks[oldest_ack] = time()
                return IterationStatus.BUSY
        
        if self.done:
            fin_send_packet: Packet = self._build_packet(Flags.SEND | Flags.FIN)
            fin_send_packet.header.transfer_id = self.__transfer_id
            
            self._send(fin_send_packet)

            return IterationStatus.FINISHED
        
        if self.__last_recv_time + self.__timeout < time():
            return IterationStatus.FINISHED
        
        return IterationStatus.SLEEP