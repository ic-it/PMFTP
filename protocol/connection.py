import logging
from random import randint
import time

from io import SEEK_END, SEEK_SET, BytesIO, FileIO
from tempfile import NamedTemporaryFile
from typing import Callable, Type, TypeVar

from .types.flags import Flags
from .types.header import Header, HEADER_SIZE
from .types.keychain import Keychain
from .types.handlers import Handlers
from .types.conn_side import ConnSide
from .types.packets.base import Packet
from .types.packets.syn import SynPacket
from .transfers.recv import RecvTransfer
from .transfers.send import SendTransfer
from .types.packets.syn_ack import SynAckPacket
from .types.packets.send_part import SendPartPacket
from .types.iteration_status import IterationStatus
from .types.packets.syn_send_msg import SynSendMsgPacket
from .types.conversation_status import ConversationStatus
from .types.packets.syn_send_file import SynSendFilePacket


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
        self.__keep_alive = 2

        self.__transfers: dict[int, tuple[RecvTransfer | SendTransfer, BytesIO]] = {}

        self._add_iterator = NotImplemented

        self._size_of_accepted_headers = 0

    @property
    def other_side(self) -> ConnSide:
        return self.__other_side
    
    @property
    def transfers_count(self) -> int:
        return len(self.__transfers)
    
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

    def _recv(self, data: bytes) -> None:
        self.__sequence_number += 1
        self.__last_time = time.time()

        packet = Packet().load(data)

        LOG.debug(f"Recived {len(data)} bytes from {self.other_side} with {packet.header.flags.__repr__()} flags")

        if not packet.is_packet_valid:
            self._send(self._build_packet(Flags.UNACK, packet.header.seq_number))
            LOG.warning(f"Packet is not valid")
            return
        
        if not packet.header.flags == (Flags.ACK | Flags.UNACK): # test doimplementacji
            self._size_of_accepted_headers += HEADER_SIZE

        if packet.header.timeout != 0 and packet.header.timeout < time.time():
            LOG.warning(f"Packet is timed out")
            return
        
        packet._private_key = self.__keychain.private_key

        if packet.header.transfer_id in self.__transfers:
            transfer, buffer = self.__transfers[packet.header.transfer_id]
            transfer._recv(packet.downcast(SendPartPacket))
            return
        self.__packet_queue.append(packet)

    
    def _send(self, packet: Packet) -> None:
        if not packet.header.flags == (Flags.ACK | Flags.UNACK): # test doimplementacji
            self._size_of_accepted_headers += HEADER_SIZE

        LOG.debug(f"Sending {packet.header.flags.__repr__()} flags to {self.other_side}")
        self.__send_proxy(self.other_side, packet.dump())
        if packet.header.transfer_id:
            return
        self.__wait_for_acknowledgment.append(packet)
        self.conversation_status.new_packet(packet)
    
    def connect(self) -> None:
        LOG.debug(f"Connecting to {self.other_side}")

        packet = self._build_packet(Flags.SYN, packet_factory=SynPacket)
        packet.public_key = self.__keychain.public_key

        self._send(packet)
    
    def disconnect(self) -> None:
        LOG.debug(f"Disconnecting from {self.other_side}")

        for transfer, _ in self.__transfers.values():
            transfer.kill()

        packet = self._build_packet(Flags.FIN)
        self._send(packet)
    
    def send_message(self, message: bytes, fragment_size: int | None = None) -> SendTransfer:
        if not self.conversation_status.is_connected:
            LOG.error(f"Connection is not established")
            raise Exception("Connection is not established")

        bio = BytesIO(message)

        transfer = SendTransfer(self.__keychain.copy(), bio, Flags.MSG, fragment_size)
        transfer._send = self._send
        transfer._build_packet = self._build_packet

        packet = self._build_packet(
            Flags.SYN | Flags.SEND | Flags.MSG,
            packet_factory=SynSendMsgPacket
        )
        packet._public_key = self.__keychain.other_public_key
        packet.message_len = len(message)
        packet.header.transfer_id = transfer.transfer_id
        self._send(packet.encrypt())

        self.__transfers[transfer.transfer_id] = (transfer, bio)
        self._add_iterator(transfer._iterate)

        return transfer
    
    def send_file(self, file_io: FileIO, fragment_size: int | None = None) -> SendTransfer:
        if not self.conversation_status.is_connected:
            LOG.error(f"Connection is not established")
            raise Exception("Connection is not established")
        
        file_io.seek(0, SEEK_END)
        file_size = file_io.tell()
        file_io.seek(0)

        transfer = SendTransfer(self.__keychain.copy(), file_io, Flags.FILE, fragment_size)
        transfer._send = self._send
        transfer._build_packet = self._build_packet

        packet = self._build_packet(
            Flags.SYN | Flags.SEND | Flags.FILE,
            packet_factory=SynSendFilePacket
        )
        packet._public_key = self.__keychain.other_public_key
        packet.filename = file_io.name
        packet.data_len = file_size

        packet.header.transfer_id = transfer.transfer_id
        self._send(packet.encrypt())

        self.__transfers[transfer.transfer_id] = (transfer, file_io)
        self._add_iterator(transfer._iterate)

        return transfer
    
    def _keep_alive(self) -> bool:
        unuck_keep_alive = [packet for packet in self.__wait_for_acknowledgment if packet.header.flags == (Flags.ACK | Flags.UNACK)]

        if len(unuck_keep_alive) > 3:
            LOG.error(f"[_keep_alive] Connection is not established or is broken")
            self.disconnect()
            self.conversation_status.is_incorrect_disconnected = True
            return False

        if not self.conversation_status.is_connected and time.time() - self.__last_time > self.__keep_alive:
            self.connect()
            self.__last_time = time.time()
            return True

        if time.time() - self.__last_time > self.__keep_alive:
            self._send(self._build_packet(Flags.ACK | Flags.UNACK))
            self.__last_time = time.time()
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
    
    def _process_fin_ack(self, packet: Packet) -> None:
        ...
    
    def _process_ack_unack(self, packet: Packet) -> None: # keep alive
        self._send_ack(packet)

    def _process_syn_send(self, packet: Packet) -> None:
        if packet.header.flags & Flags.MSG == Flags.MSG:
            self._process_syn_send_msg(packet.downcast(SynSendMsgPacket))
        elif packet.header.flags & Flags.FILE == Flags.FILE:
            self._process_syn_send_file(packet.downcast(SynSendFilePacket))
    
    def _process_syn_send_msg(self, packet: SynSendMsgPacket) -> None:
        packet._private_key = self.__keychain.private_key
        packet.decrypt()

        bio = BytesIO(b'')
        transfer = RecvTransfer(
            packet.message_len,
            packet.header.transfer_id,
            self.__keychain,
            bio,
            Flags.MSG
        )
        transfer._send = self._send
        transfer._build_packet = self._build_packet
        self.__transfers[packet.header.transfer_id] = transfer, bio
        self._add_iterator(transfer._iterate)
    
    def _process_syn_send_file(self, packet: SynSendFilePacket) -> None:
        packet._private_key = self.__keychain.private_key
        packet.decrypt()

        bio = NamedTemporaryFile('w+b', delete=True)
        transfer = RecvTransfer(
            packet.data_len,
            packet.header.transfer_id,
            self.__keychain,
            bio,
            Flags.FILE,
            packet.filename
        )
        transfer._send = self._send
        transfer._build_packet = self._build_packet
        self.__transfers[packet.header.transfer_id] = transfer, bio
        self._add_iterator(transfer._iterate)


    def _iterate(self) -> IterationStatus:
        if self.conversation_status.is_disconnected and len(self.__transfers) == 0 or not self._keep_alive():
            for transfer_id, (transfer, io_) in list(self.__transfers.items()):
                transfer.kill()
            
            self.__handlers.on_disconnect(self)
            return IterationStatus.FINISHED
        
        for transfer_id, (transfer, io_) in list(self.__transfers.items()):
            if isinstance(transfer, RecvTransfer) and transfer.done:
                if transfer.data_type == Flags.MSG:
                    self.__handlers.on_message(self, io_.getvalue(), transfer.is_correct)
                if transfer.data_type == Flags.FILE:
                    self.__handlers.on_file(self, io_, transfer.filename, transfer.is_correct)
            
            if transfer.done:
                del self.__transfers[transfer_id]
            

        while len(self.__packet_queue) > 0:

            packet = self.__packet_queue.pop(0)
            self.conversation_status.new_packet(packet)
            
            if packet.header.flags == Flags.SYN:
                self._process_syn(packet.downcast(SynPacket))
            
            if packet.header.flags == (Flags.SYN | Flags.ACK):
                self._process_syn_ack(packet.downcast(SynAckPacket))
            
            if not self.conversation_status.is_connected:
                continue

            if packet.header.flags == Flags.FIN:
                self._process_fin(packet)
            
            if packet.header.flags & (Flags.SYN | Flags.SEND) == (Flags.SYN | Flags.SEND):
                self._process_syn_send(packet)

            if packet.header.flags == (Flags.FIN | Flags.ACK):
                self._process_fin_ack(packet)
            
            if packet.header.flags == (Flags.ACK | Flags.UNACK):
                self._process_ack_unack(packet)
            
            if packet.header.flags & Flags.ACK:
                self._recv_ack(packet)
    
        return IterationStatus.SLEEP