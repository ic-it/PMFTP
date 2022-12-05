from io import BytesIO
from time import time
from typing import Type, TypeVar
from ..types.flags import Flags
from ..types.packets.base import Packet
from ..types.packets.send_part import SendPartPacket
from ..types.iteration_status import IterationStatus
from ..types.keychain import Keychain


_T = TypeVar("_T")

class RecvTransfer:
    def __init__(self, 
                 length: int, 
                 transfer_id: int, 
                 keychain: Keychain,
                 recv_stram: BytesIO) -> None:
        self.__last_received_time = 0
        self.__timeout = 5
        self.__premature_processing_time = 0.1
        self.__length = length
        self.__window: list[SendPartPacket] = []
        self.__window_size = 10
        self.__transfer_id = transfer_id
        self.__recv_stram = recv_stram
        self.__recived_data_length = 0
        self.__keychain = keychain
    
    def _build_packet(self, flags: Flags, ack_number: int = 0, data: bytes = b'', packet_factory: Type[_T] = Packet) -> _T: NotImplemented
    def _send(self, packet: Packet) -> None: NotImplemented
    
    def _recv(self, packet: SendPartPacket) -> None:
        self.__last_received_time = time()
        self.__window.append(packet)
        self.__window.sort(key=lambda x: x.header.seq_number)
    
    def _is_transfer_finished(self) -> bool:
        return self.__recived_data_length == self.__length
    
    def _process_window(self) -> None:
        sq_nums = []
        while len(self.__window) > 0:
            packet = self.__window.pop(0)
            self.__recv_stram.seek(packet.insertion_point)
            self.__recv_stram.write(packet.data)
            self.__recived_data_length += len(packet.data)
            sq_nums.append(packet.header.seq_number)

        ack_packet: Packet = self._build_packet(Flags.ACK)
        ack_packet.header.transfer_id = self.__transfer_id
        ack_packet.data = b':'.join(
            map(
                lambda x: x.to_bytes(4, 'big'),
                sq_nums
            )
        )
        ack_packet._public_key = self.__keychain.public_key
        self._send(ack_packet)

    def _iterate(self) -> IterationStatus:
        if self.__recived_data_length == self.__length:
            return IterationStatus.FINISHED
        
        if self.__last_received_time + self.__timeout < time():
            return IterationStatus.FINISHED
        
        if len(self.__window) == 0:
            return IterationStatus.SLEEP
        
        if len(self.__window) >= self.__window_size or self.__last_received_time + self.__premature_processing_time < time():
            self._process_window()
        
        return IterationStatus.SLEEP