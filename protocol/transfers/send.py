import io
import random
import logging

from io import BytesIO
from time import time
from typing import Type, TypeVar, Generator
from ..types.flags import Flags
from ..types.packets.base import Packet
from ..types.header import Header, HEADER_SIZE
from ..types.packets.send_part import SendPartPacket
from ..types.iteration_status import IterationStatus
from ..types.keychain import Keychain


LOG = logging.getLogger("SendTransfer")
LOG.green = lambda x: LOG.info(f"\033[92m{x}\033[0m" + " "*20)
LOG.red = lambda x: LOG.info(f"\033[91m{x}\033[0m" + " "*20)
LOG.gray = lambda x: LOG.info(f"\033[90m{x}\033[0m" + " "*20)
LOG.yellow = lambda x: LOG.info(f"\033[93m{x}\033[0m" + " "*20)
LOG.cyan = lambda x: LOG.info(f"\033[96m{x}\033[0m" + " "*20)

_T = TypeVar("_T")

PART_SIZE = 1024-HEADER_SIZE-10 # 1024 - header - 10 bytes for part number

class SendTransfer:
    def __init__(self,
                 keychain: Keychain,
                 send_stram: BytesIO,
                 data_type: Flags,
                 part_size: int | None = PART_SIZE
                 ) -> None:
        self.__last_recv_time = time()
        
        self.__timeout = 30
        self.__packet_timeout = 3
        self.__window: dict[SendPartPacket, int] = {}
        self.__window_size = 30
        self.__transfer_id = random.randint(0, 2**16)
        self.__keychain = keychain
        self.__data_type = data_type
    
        if part_size is None:
            part_size = PART_SIZE

        if part_size > PART_SIZE - 30 or part_size <= 0 and part_size is not None:
            raise ValueError(f"Part size must be between 1 and {PART_SIZE-30}")
        
        self.__part_size = part_size

        self.__send_stram = send_stram
        self.__send_stram.seek(0, io.SEEK_END)
        self.__data_len = self.__send_stram.tell()
        self.__send_stram.seek(0)

        self._get_parts_iter = self._get_parts()
        self._build_packet = NotImplemented
        self._send = NotImplemented
        self._done = False
        self._got_fin = False
        self.__killed = False

        LOG.info(f"Transfer ID: {self.__transfer_id}")

    @property
    def transfer_id(self) -> int:
        return self.__transfer_id
    
    @property
    def done(self) -> bool:
        if self.__last_recv_time + self.__timeout < time():
            LOG.red("Transfer timed out")
            self.kill()
        return self._got_fin or self.__killed
    
    @property
    def progress(self) -> float:
        return self.__send_stram.tell() / (self.__data_len or 1) * 100
    
    @property
    def window_fill(self) -> int:
        return len(self.__window)
    
    @property
    def data_type(self) -> Flags:
        return self.__data_type
    
    def kill(self) -> None:
        self.__killed = True

    def _recv(self, packet: SendPartPacket) -> None:
        self.__last_recv_time = time()
        packet.decrypt()
        
        if packet.header.flags & Flags.ACK:
            LOG.yellow(f"Window size " + f"{len(self.__window)}")

            for i, pos in enumerate((int.from_bytes(packet.data[i:i+8], 'big') for i in range(0, len(packet.data), 8))):
                self.__window = {p: ins_p for p, ins_p in self.__window.items() if ins_p != pos}

            ack_packet: Packet = self._build_packet(Flags.ACK, ack_number=packet.header.seq_number)
            ack_packet.header.transfer_id = self.__transfer_id
            self._send(ack_packet)

            LOG.green(f"Got {i+1} ACKs ")
        
        if packet.header.flags & Flags.FIN:
            self._got_fin = True
    
    def _get_parts(self) -> Generator[tuple[bytes, int], None, None]:
        self.__send_stram.seek(0)
        while True:
            position = self.__send_stram.tell()
            data = self.__send_stram.read(self.__part_size)

            if len(data) == 0:
                break
            yield data, position
    
    def _resend_packets_in_window(self) -> IterationStatus:
        if not self.__window:
            return IterationStatus.SLEEP
        
        oldes_packet, position = min(self.__window.items(), key=lambda x: x[0].header.timeout)
        if oldes_packet.header.timeout > time():
            return IterationStatus.SLEEP
        
        new_packet: Packet = self._build_packet(oldes_packet.header.flags)
        new_packet.data = oldes_packet.data
        new_packet.header.transfer_id = self.__transfer_id
        new_packet.header.timeout = time() + self.__packet_timeout
        self._send(new_packet)
        
        self.__window[new_packet] = position
        del self.__window[oldes_packet]

        LOG.red(f"Resending packet [{new_packet.header.seq_number}]")
        return IterationStatus.BUSY
    
    def _send_packet_part(self) -> IterationStatus:
        if len(self.__window) >= self.__window_size:
            return IterationStatus.SLEEP

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
        packet.header.timeout = self.__packet_timeout + time()
        packet.encrypt()
        
        self.__window[packet] = position
        self._send(packet)
        
        return IterationStatus.BUSY

    def _iterate(self) -> IterationStatus:
        if self.done:
            fin_send_packet: Packet = self._build_packet(Flags.SEND | Flags.FIN)
            fin_send_packet.header.transfer_id = self.__transfer_id

            LOG.info(f"Sending FIN packet [{fin_send_packet.header.seq_number}] [{self._got_fin=} or {(self.__last_recv_time + self.__timeout < time())=} or {self.__killed=}]")
            self._send(fin_send_packet)

            if self.__timeout + self.__last_recv_time < time():
                LOG.info("Transfer timed out")
            return IterationStatus.FINISHED
        
        if self._resend_packets_in_window() == IterationStatus.BUSY:
            return IterationStatus.BUSY
        
        if self._send_packet_part() == IterationStatus.BUSY:
            return IterationStatus.BUSY

        return IterationStatus.SLEEP
