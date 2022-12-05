from .flags import Flags
from .packets.base import Packet


class ConversationStatus:
    def __init__(self) -> None:
        self.__is_connected: bool = False
        self.__is_connecting: bool = False
        self.__is_disconnected: bool = False
        self.__is_incorrect_disconnected: bool = False
    
    @property
    def is_connected(self) -> bool:
        return self.__is_connected
    
    @property
    def is_connecting(self) -> bool:
        return self.__is_connecting

    @property
    def is_disconnected(self) -> bool:
        return self.__is_disconnected or self.__is_incorrect_disconnected
    
    @property
    def is_incorrect_disconnected(self) -> bool:
        return self.__is_incorrect_disconnected
    
    @is_incorrect_disconnected.setter
    def is_incorrect_disconnected(self, value: bool) -> None:
        self.__is_incorrect_disconnected = value
        if value:
            self.__is_connected = False
            self.__is_connecting = False
            self.__is_disconnected = False
    
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
            self.__is_disconnected = True
            self.__is_connected = False
        if packet.header.flags == (Flags.FIN | Flags.ACK):
            self.__is_disconnected = True
            self.__is_connected = False
    
    def __str__(self) -> str:
        return f"ConversationStatus({self.is_connected=}, {self.is_connecting=}, {self.is_disconnected=})"