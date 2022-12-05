from io import BytesIO
import logging
import time

from typing import Callable, Type, TypeVar
from .types.packets.send_part_msg import SendPartMsgPacket
from .types.packets.syn_send_msg import SynSendMsgPacket
from .types.flags import Flags
from .types.iteration_status import IterationStatus
from .types.conn_side import ConnSide
from .types.packets.base import Packet
from .types.packets.syn import SynPacket
from .types.packets.syn_ack import SynAckPacket
from .types.header import Header
from .types.keychain import Keychain
from .types.conversation_status import ConversationStatus
from .types.handlers import Handlers
from .transfers.recv import RecvTransfer


LOG = logging.getLogger("Connection")
_T = TypeVar("_T")

class Connection:
    def __init__(self, other_side: ConnSide, 
                 keychain: Keychain,
                 send_proxy: Callable[[ConnSide, bytes], None],
                 handlers: Handlers,
                 ) -> None:
        
        self.__other_side: ConnSide = other_side
        self.__packet_queue: list[Packet] = []
        self.__keychain: Keychain = keychain
        self.__handlers: Handlers = handlers
        self.__send_proxy = send_proxy
        self.conversation_status: ConversationStatus = ConversationStatus()
        
        self.__sequence_number = 0
        self.__window_size = 10
        self.__wait_for_acknowledgment: list[Packet] = []
        self.__last_time = time.time()
        self.__keep_alive = 5

        self.__transfers: dict[int, (RecvTransfer, BytesIO)] = {}

    @property
    def other_side(self) -> ConnSide:
        return self.__other_side
    
    def _build_header(self, flags: Flags, ack_number: int) -> Header:
        self.__sequence_number += 1
        return Header(seq_number=self.__sequence_number,
                      ack_number=ack_number,
                      flags=flags)
    
    def _build_packet(self, flags: Flags, ack_number: int = 0, data: bytes = b'', packet_factory: Type[_T] = Packet) -> _T:
        header = self._build_header(flags, ack_number)
        packet = packet_factory(header=header)
        packet.data = data
        return packet
    
    def _add_iterator(self, iterator: Callable) -> None: NotImplemented

    def _recv(self, data: bytes) -> None:
        self.__sequence_number += 1
        self.__last_time = time.time()

        packet = Packet().load(data)

        LOG.debug(f"RECV: {packet}")

        if not packet.is_packet_valid:
            self._send(self._build_packet(Flags.UNACK, packet.header.seq_number))
            LOG.debug(f"Packet is not valid")
            return
        
        packet._private_key = self.__keychain.private_key
        self.__packet_queue.append(packet)
    
    def _send(self, packet: Packet) -> None:
        LOG.debug(f"SEND: {packet}")
        self.__send_proxy(self.other_side, packet.dump())
        self.__wait_for_acknowledgment.append(packet)
        self.conversation_status.new_packet(packet)
    
    def connect(self) -> None:
        LOG.debug(f"Connecting to {self.other_side}")

        packet = self._build_packet(Flags.SYN, packet_factory=SynPacket)
        packet.public_key = self.__keychain.public_key

        self._send(packet)
    
    def disconnect(self) -> None:
        LOG.debug(f"Disconnecting from {self.other_side}")

        packet = self._build_packet(Flags.FIN)
        self._send(packet)
    
    def send_message(self, message: bytes) -> None:
        if not self.conversation_status.is_connected:
            LOG.debug(f"Connection is not established")
            raise Exception("Connection is not established")
        
        packet = self._build_packet(
            Flags.SYN | Flags.SEND | Flags.MSG,
            packet_factory=SynSendMsgPacket
        )
        packet._public_key = self.__keychain.other_public_key
        packet.message_len = len(message)
        self._send(packet.encrypt())

        send_part = self._build_packet(
            Flags.SEND | Flags.PART | Flags.MSG,
            packet_factory=SendPartMsgPacket
        )
        send_part._public_key = self.__keychain.other_public_key
        send_part.insertion_point = 0
        send_part.message = message
        self._send(send_part.encrypt())
    
    def _keep_alive(self) -> bool:
        if time.time() - self.__last_time > self.__keep_alive:
            self._send(self._build_packet(Flags.ACK | Flags.UNACK))
            self.__last_time = time.time()
        
        unuck_keep_alive = [packet for packet in self.__wait_for_acknowledgment if packet.header.flags == (Flags.ACK | Flags.UNACK)]

        if len(unuck_keep_alive) > 3:
            self.disconnect()
            self.conversation_status.is_incorrect_disconnected = True
            return False
        return True
    
    def _send_ack(self, packet: Packet) -> None:
        self._send(self._build_packet(Flags.ACK, packet.header.seq_number))
    
    def _recv_ack(self, packet: Packet) -> None:
        self.__wait_for_acknowledgment = [p for p in self.__wait_for_acknowledgment if p.header.seq_number != packet.header.ack_number]
    
    def _process_syn(self, packet: SynPacket) -> None:
        self.__keychain.other_public_key = packet.public_key

        new_packet = self._build_packet(Flags.SYN | Flags.ACK, packet.header.seq_number, packet_factory=SynAckPacket)
        new_packet.public_key = self.__keychain.public_key
        
        self._send(new_packet)
        self.__handlers.on_connect(self) # TODO: Remake
    
    def _process_syn_ack(self, packet: SynAckPacket) -> None:
        self.__keychain.other_public_key = packet.public_key

        self._send_ack(packet)
        self.__handlers.on_connect(self) # TODO: Remake
    
    def _process_fin(self, packet: Packet) -> None:
        new_packet = self._build_packet(Flags.FIN | Flags.ACK, packet.header.seq_number)
        
        self._send(new_packet)
        self.__handlers.on_disconnect(self)
    
    def _process_fin_ack(self, packet: Packet) -> None:
        self.__handlers.on_disconnect(self)
    
    def _process_ack_unack(self, packet: Packet) -> None: # keep alive
        self._send_ack(packet)

    def _process_syn_send(self, packet: Packet) -> None:
        if packet & Flags.MSG:
            self._process_syn_send_msg(packet.downcast(SynSendMsgPacket))
    
    def _process_syn_send_msg(self, packet: SynSendMsgPacket) -> None:
        packet._private_key = self.__keychain.private_key
        packet.decrypt()

        bio = BytesIO()
        transfer = RecvTransfer(
            packet.message_len,
            packet.header.transfer_id,
            self.__keychain,
            bio
        )
        self.__transfers[packet.header.transfer_id] = transfer, bio
        self._add_iterator(transfer._iterate)



    def _iterate(self) -> IterationStatus:
        if not self._keep_alive():
            return IterationStatus.FINISHED

        while len(self.__packet_queue) > 0:

            packet = self.__packet_queue.pop(0)
            self.conversation_status.new_packet(packet)
            
            if packet.header.flags == Flags.SYN:
                self._process_syn(packet.downcast(SynPacket))
            
            if packet.header.flags == (Flags.SYN | Flags.ACK):
                self._process_syn_ack(packet.downcast(SynAckPacket))
            
            if packet.header.flags & (Flags.SYN | Flags.SEND):
                packet = packet.downcast(SynSendMsgPacket)
                packet._private_key = self.__keychain.private_key
                packet.decrypt()
                print(packet.message_len)
            
            # if packet.header.flags == Flags.SEND | Flags.PART | Flags.MSG:
            #     packet = packet.downcast(SendPartMsgPacket)
            #     packet._private_key = self.__keychain.private_key
            #     packet.decrypt()
            #     print(packet.message)

            if packet.header.flags == Flags.FIN:
                self._process_fin(packet)

            if packet.header.flags == (Flags.FIN | Flags.ACK):
                self._process_fin_ack(packet)
            
            if packet.header.flags == (Flags.ACK | Flags.UNACK):
                self._process_ack_unack(packet)
            
            if packet.header.flags & Flags.ACK:
                self._recv_ack(packet)
        
        if self.conversation_status.is_disconnected:
            return IterationStatus.FINISHED
    
        return IterationStatus.SLEEP