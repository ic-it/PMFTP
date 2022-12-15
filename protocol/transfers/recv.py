import logging

from io import BytesIO
from time import time
from ..types.flags import Flags
from typing import Type, TypeVar
from ..types.keychain import Keychain
from ..types.packets.base import Packet
from ..types.packets.send_part import SendPartPacket
from ..types.iteration_status import IterationStatus


LOG = logging.getLogger("RecvTransfer")

LOG.green = lambda x: LOG.debug(f"\033[92m{x}\033[0m" + " "*20)
LOG.red = lambda x: LOG.debug(f"\033[91m{x}\033[0m" + " "*20)
LOG.gray = lambda x: LOG.debug(f"\033[90m{x}\033[0m" + " "*20)
LOG.yellow = lambda x: LOG.debug(f"\033[93m{x}\033[0m" + " "*20)
LOG.cyan = lambda x: LOG.debug(f"\033[96m{x}\033[0m" + " "*20)

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

        self.__timeout = 30
        self.__ack_timeout = 10
        self.__process_window_tick = 0.01

        self.__max_ack_size = 100

        self.__length = length
        self.__window: list[SendPartPacket] = []
        self.__processed_packets: list[int] = []
        self.__transfer_id = transfer_id
        self.__recv_stram = recv_stram
        self.__recived_data_length = 0
        self.__keychain = keychain
        self._build_packet = NotImplemented
        self._send = NotImplemented
        self.__data_type = data_type
        self.__filename = filename

        self.__got_fin = False
        self.__killed = False

        self._acks: dict[SendPartPacket, int] = {}

        LOG.info(f"Transfer ID: {self.__transfer_id}")
    
    def _recv(self, packet: SendPartPacket) -> None:
        if self.done:
            LOG.yellow(f"Transfer already done [{self.__recived_data_length == self.__length=}, {self.__got_fin=}, {self.__killed=}]")
            return
        
        self.__last_recv_time = time()
        
        if packet.header.flags & Flags.ACK:
            LOG.green(f"Got ACK packet [{packet.header.ack_number}] {len(self._acks)}")
            self._acks = {p: t for p, t in self._acks.items() if p.header.seq_number != packet.header.ack_number}
            return
        
        if packet.header.flags & Flags.FIN:
            LOG.info("Got FIN packet")
            self.__got_fin = True
            return
        
        if packet.header.flags & Flags.PART == Flags.PART:
            if packet.header.timeout < time():
                LOG.red(f"Packet [{packet.insertion_point}] timeout")
                return
            self.__window.append(packet.decrypt())

    @property
    def is_correct(self) -> bool:
        return self.__recived_data_length == self.__length
    
    @property
    def done(self) -> bool:
        if self.is_correct:
            return True
        
        if (self.__last_recv_time + self.__timeout < time()) or self.__got_fin or self.__killed: 
            self.kill()

        return self.__killed

    @property
    def data_type(self) -> Flags:
        return self.__data_type
    
    @property
    def filename(self) -> bytes | None:
        return self.__filename
    
    @property
    def progress(self) -> float:
        return (self.__recived_data_length / (self.__length or 1)) * 100
    
    def kill(self) -> None:
        self.__killed = True
    
    def _process_window(self) -> IterationStatus:
        if not len(self.__window) or self.__last_process_time + self.__process_window_tick >= time():
            return IterationStatus.SLEEP
        insertion_points: list[int] = []

        LOG.gray(f"Processing window [{len(self.__window)} packets]")
        while len(insertion_points) < self.__max_ack_size and len(self.__window):
            packet = self.__window.pop()
            insertion_points.append(packet.insertion_point)

            if packet.insertion_point in self.__processed_packets:
                LOG.yellow(f"Got already processed packet [{packet.insertion_point}][{len(self.__processed_packets)}]")
                continue
            self.__recv_stram.seek(packet.insertion_point)
            self.__recv_stram.write(packet.data_part)
            self.__recived_data_length += len(packet.data_part)
            self.__processed_packets.append(packet.insertion_point)
    
        if not insertion_points:
            return IterationStatus.SLEEP
        
        ack_packet: Packet = self._build_packet(Flags.ACK)
        ack_packet.header.transfer_id = self.__transfer_id
        
        ack_packet.data = b''
        for i in insertion_points:
            ack_packet.data += i.to_bytes(8, 'big')
        

        LOG.green(f"Sending ACK packet [{ack_packet.header.seq_number}][{len(insertion_points)} packets]")

        ack_packet._public_key = self.__keychain.other_public_key
        ack_packet.encrypt()

        self._acks[ack_packet] = time()
        self._send(ack_packet)

        self.__last_process_time = time()
        return IterationStatus.BUSY

    def _resend_old_acks(self) -> IterationStatus:
        if not len(self._acks):
            return IterationStatus.SLEEP
        
        oldest_ack, time_ = min(self._acks.items(), key=lambda x: x[1])
        if time_ + self.__ack_timeout >= time():
            return IterationStatus.SLEEP

        new_packet: Packet = self._build_packet(Flags.ACK)
        new_packet.data = oldest_ack.data
        new_packet.header.transfer_id = self.__transfer_id

        self._send(new_packet)
        self._acks[new_packet] = time()
        del self._acks[oldest_ack]

        LOG.red(f"Resending ACK packet [{oldest_ack.header.seq_number}]")

        return IterationStatus.BUSY
        

    def _iterate(self) -> IterationStatus:
        if self.done:
            fin_send_packet: Packet = self._build_packet(Flags.SEND | Flags.FIN)
            fin_send_packet.header.transfer_id = self.__transfer_id
            
            LOG.info(f"Sending FIN packet [{fin_send_packet.header.seq_number}]")
            if self.__last_recv_time + self.__timeout < time():
                LOG.info("Transfer timed out")

            self._send(fin_send_packet)

            return IterationStatus.FINISHED
        
        if self._resend_old_acks() == IterationStatus.BUSY:
            return IterationStatus.BUSY

        if self._process_window() == IterationStatus.BUSY:
            return IterationStatus.BUSY

        return IterationStatus.SLEEP