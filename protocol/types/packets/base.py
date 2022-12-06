import copy

from typing import Type, TypeVar
from ..header import Header, HEADER_SIZE
from ...utils import PUBLIC_KEY_T, PRIVATE_KEY_T, encrypt, decrypt


_T = TypeVar("_T", bound="Packet")

class Packet:
    def __init__(self, header: Header = None, 
                public_key: PUBLIC_KEY_T = None, private_key: PRIVATE_KEY_T = None,
                *args, **kwargs) -> None:
        if not header:
            self.__header = Header()
        else:
            self.__header = header

        self.data = b'' ## XD вообще хз

        self.__public_key = public_key
        self.__private_key = private_key

        self._post_init_(*args, **kwargs)
    
    def _post_init_(self, *args, **kwargs) -> None: NotImplemented

    @property
    def is_packet_valid(self) -> bool:
        return self.__validate_checksum()

    @property
    def _public_key(self) -> PUBLIC_KEY_T:
        return self.__public_key
    
    @_public_key.setter
    def _public_key(self, public_key: PUBLIC_KEY_T) -> None:
        self.__public_key = public_key
    
    @property
    def _private_key(self) -> PRIVATE_KEY_T:
        return self.__private_key
    
    @_private_key.setter
    def _private_key(self, private_key: PRIVATE_KEY_T) -> None:
        self.__private_key = private_key
    
    @property
    def header(self) -> Header:
        return self.__header
    
    @property
    def data(self) -> bytes:
        return self.__data
    
    @data.setter
    def data(self, data: bytes) -> None:
        if data is None:
            data = b''

        self.__data = data
        self.__header.checksum = self.__calculate_checksum()
    
    def __calculate_checksum(self) -> int:
        checksum = 0
        temp_data = copy.copy(self.__data)
        if len(temp_data) % 2 == 1:
            temp_data += b'\x00'
        
        for i in range(0, len(temp_data), 2):
            checksum += int.from_bytes(temp_data[i:i+2], byteorder='big')
        
        return checksum & 0b1111111111111111
    
    def encrypt(self: _T) -> _T:
        self.data = encrypt(self.data, self._public_key)
        return self
    
    def decrypt(self: _T) -> _T:
        self.data = decrypt(self.data, self._private_key)
        return self

    def __validate_checksum(self) -> bool:
        return self.__header.checksum == self.__calculate_checksum()
    
    def dump(self) -> bytes:
        return self.__header.dump() + self.__data
    
    def load(self: _T, data: bytes) -> _T:
        self.__header.load(data[:HEADER_SIZE])
        self.__data = data[HEADER_SIZE:]
        return self
    
    def copy(self: _T) -> _T:
        return self.downcast(type(self))

    def downcast(self, packet_type: Type[_T]) -> _T:
        packet = packet_type()
        packet.__header = self.__header
        packet.__data = self.__data
        packet.__public_key = self.__public_key
        packet.__private_key = self.__private_key
        return packet

    def __str__(self) -> str:
        return f"Packet(header={self.__header.__str__()}, data={self.__data})"
    
    def __repr__(self) -> str:
        return self.__str__()