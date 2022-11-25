import logging
import time

from typing import Callable, Generator, Type, TypeVar

from .types.packets.send_part_msg import SendPartMsgPacket
from .types.packets.syn_send_msg import SynSendMsgPacket
from .types.flags import Flags
from .types.iterable_in_loop import IterableInLoop
from .types.iteration_status import IterationStatus
from .types.conn_side import ConnSide
from .types.packets.base import Packet
from .types.packets.syn import SynPacket
from .types.packets.syn_ack import SynAckPacket
from .types.header import Header
from .utils import PUBLIC_KEY_T, PRIVATE_KEY_T
from .types.conversation_status import ConversationStatus

LOG = logging.getLogger("Connection")

_T = TypeVar("_T")

class Connection:
    def __init__(self, other_side: ConnSide, 
                 public_key: PUBLIC_KEY_T, private_key: PRIVATE_KEY_T,
                 send_proxy: Callable[[ConnSide, bytes], None]) -> None:
        self.__other_side: ConnSide = other_side
        self.__packet_queue: list[Packet] = []
        self.__other_public_key: PUBLIC_KEY_T = None
        self.__public_key: PUBLIC_KEY_T = public_key
        self.__private_key: PRIVATE_KEY_T = private_key
        self._conversation_status: ConversationStatus = ConversationStatus()
        self.__send_proxy = send_proxy
        
        self.__sequence_number = 0
        self.__window_size = 0
        self.__un_acknowledgment: list[Packet] = []
        self.__last_time = time.time()
        self.__keep_alive = 3

        self.__sending_data = [
            
        ]

    @property
    def other_side(self) -> ConnSide:
        return self.__other_side
    
    def _build_header(self, flags: Flags, ack_number: int) -> Header:
        self.__sequence_number += 1
        return Header(
            seq_number=self.__sequence_number,
            ack_number=ack_number,
            flags=flags,
            window_size=self.__window_size
        )
    
    def _build_packet(self, flags: Flags, ack_number: int = 0, data: bytes = b'', packet_factory: Type['_T'] = Packet) -> Type['_T']:
        header = self._build_header(flags, ack_number)
        packet = packet_factory(header=header, public_key=self.__other_public_key, private_key=self.__private_key)
        packet.data = data
        return packet

    def recv(self, data: bytes) -> None:
        self.__sequence_number += 1
        self.__last_time = time.time()

        packet: Packet = Packet().load(data)

        packet.public_key = self.__public_key
        packet.private_key = self.__private_key

        LOG.debug(f"RECV: flags={packet.header.flags.__repr__()}, seq_number={packet.header.seq_number}, ack_number={packet.header.ack_number}, data_len={len(packet.data)}")

        for unack_packet in self.__un_acknowledgment:
            if unack_packet.header.seq_number == packet.header.ack_number:
                self.__un_acknowledgment.remove(unack_packet)
                break

        self.__packet_queue.append(packet)
    
    def _send(self, packet: Packet) -> None:
        LOG.debug(f"SEND: flags={packet.header.flags.__repr__()}, seq_number={packet.header.seq_number}, ack_number={packet.header.ack_number}, data_len={len(packet.data)}")
        self.__send_proxy(self.other_side, packet.dump())
        self.__un_acknowledgment.append(packet)
        self._conversation_status.new_packet(packet)
    
    def connect(self) -> None:
        LOG.debug(f"Connecting to {self.other_side}")

        packet = self._build_packet(Flags.SYN, packet_factory=SynPacket)
        packet.data_public_key = self.__public_key
        packet.window_size = self.__window_size

        self._send(packet)
    
    def disconnect(self) -> None:
        LOG.debug(f"Disconnecting from {self.other_side}")
        packet = self._build_packet(Flags.FIN)
        self._send(packet)
    
    def send_message(self, message: bytes) -> None:
        packet = self._build_packet(
            Flags.SYN | Flags.SEND | Flags.MSG,
            packet_factory=SynSendMsgPacket
        )
        packet.message_len = len(message)
        print(packet.message_len, len(message), packet.public_key, packet.private_key)
        self._send(packet)

        send_part = self._build_packet(
            Flags.SEND | Flags.PART | Flags.MSG,
            packet_factory=SendPartMsgPacket
        )
        send_part.message = message
        print(send_part)
        self._send(send_part)

        

    def process(self) -> IterationStatus:
        if time.time() - self.__last_time > 5:
            self._send(self._build_packet(Flags.ACK))
            self.__keep_alive -= 1
            self.__last_time = time.time()
        if self.__keep_alive == 0:
            self.disconnect()
            return IterationStatus.FINISHED

        while len(self.__packet_queue) > 0:
            self.__keep_alive = 3

            packet = self.__packet_queue.pop(0)
            self._conversation_status.new_packet(packet)
            
            if packet.header.flags == Flags.SYN:
                packet = SynPacket().load(packet.dump())
                self.__other_public_key = packet.data_public_key
                self.__window_size = packet.window_size
                new_packet = self._build_packet(Flags.SYN | Flags.ACK, packet.header.seq_number, packet_factory=SynAckPacket)
                new_packet.data_public_key = self.__public_key
                new_packet.window_size = self.__window_size
                self._send(new_packet)
            
            if packet.header.flags == (Flags.SYN | Flags.ACK):
                packet = SynAckPacket().load(packet.dump())
                self.__other_public_key = packet.data_public_key
                self.__window_size = packet.window_size
                new_packet = self._build_packet(Flags.ACK, packet.header.seq_number)
                self._send(new_packet)
            
            if packet.header.flags == Flags.SYN | Flags.SEND | Flags.MSG:
                packet = SynSendMsgPacket().load(packet.dump())
                packet.private_key = self.__private_key

                print(packet.message_len, packet.public_key, packet.private_key)
            
            if packet.header.flags == Flags.SEND | Flags.PART | Flags.MSG:
                packet = SendPartMsgPacket().load(packet.dump())
                packet.private_key = self.__private_key
                print(packet.message, packet.public_key, packet.private_key)

            if packet.header.flags == Flags.FIN:
                new_packet = self._build_packet(Flags.FIN | Flags.ACK, packet.header.seq_number)
                self._send(new_packet)
                return IterationStatus.FINISHED

            if packet.header.flags == (Flags.FIN | Flags.ACK):
                return IterationStatus.FINISHED
            
            # print(self.__other_public_key, self.__public_key, self.__private_key)
            # print(self._conversation_status)

        return IterationStatus.SLEEP