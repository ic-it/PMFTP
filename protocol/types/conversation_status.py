from .flags import Flags
from .packets.base import Packet

class ConversationStatus:
    def __init__(self) -> None:
        self.__is_connected: bool = False
        self.__is_connecting: bool = False
        self.__is_disconnecting: bool = False
        self.__is_disconnected: bool = False
    
    @property
    def is_connected(self) -> bool:
        return self.__is_connected
    
    @property
    def is_connecting(self) -> bool:
        return self.__is_connecting
    
    @property
    def is_disconnecting(self) -> bool:
        return self.__is_disconnecting
    
    @property
    def is_disconnected(self) -> bool:
        return self.__is_disconnected
    
    def new_packet(self, packet: Packet) -> None:
        if packet.header.flags == Flags.SYN:
            self.__is_connecting = True
            self.__is_disconnected = False
        if packet.header.flags == (Flags.SYN | Flags.ACK):
            self.__is_connecting = True
            self.__is_connected = False
        if packet.header.flags == Flags.ACK and self.__is_connecting:
            self.__is_connecting = False
            self.__is_connected = True
        if packet.header.flags == Flags.FIN:
            self.__is_disconnecting = True
            self.__is_connected = False
        if packet.header.flags == (Flags.FIN | Flags.ACK):
            self.__is_disconnecting = False
            self.__is_disconnected = True

    
    def __str__(self) -> str:
        return f"ConversationStatus(is_connected={self.is_connected}, is_connecting={self.is_connecting}, is_disconnecting={self.is_disconnecting}, is_disconnected={self.is_disconnected})"