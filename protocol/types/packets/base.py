import copy

from typing import Type, TypeVar
from ..header import Header
from ...utils import PUBLIC_KEY_T, PRIVATE_KEY_T, encrypt, decrypt

_T = TypeVar("_T", bound="Packet")

class Packet:
    def __init__(self, header: Header = None, 
                public_key: PUBLIC_KEY_T = None, private_key: PRIVATE_KEY_T = None,
                *args, **kwargs) -> None:
        self._auto_encrypt_decrypt = False

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
    def public_key(self) -> PUBLIC_KEY_T:
        return self.__public_key
    
    @public_key.setter
    def public_key(self, public_key: PUBLIC_KEY_T) -> None:
        self.__public_key = public_key
    
    @property
    def private_key(self) -> PRIVATE_KEY_T:
        return self.__private_key
    
    @private_key.setter
    def private_key(self, private_key: PRIVATE_KEY_T) -> None:
        self.__private_key = private_key
    
    @property
    def header(self) -> Header:
        return self.__header
    
    @property
    def data(self) -> bytes:
        if self._auto_encrypt_decrypt:
            return decrypt(self.__data, self.private_key)
        return self.__data
    
    @data.setter
    def data(self, data: bytes) -> None:
        if self._auto_encrypt_decrypt:
            self.__data = encrypt(data, self.public_key)
        else:
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
    
    def __validate_checksum(self) -> bool:
        return self.__header.checksum == self.__calculate_checksum()
    
    
    def dump(self) -> bytes:
        return self.__header.dump() + self.__data
    
    def load(self, data: bytes) -> 'Packet':
        self.__header.load(data[:15])
        self.__data = data[15:]
        return self
    
    def __repr__(self) -> str:
        return (
            f"Packet(header={self.__header.__repr__()}, " "\n"
            "\t" f"data={self.__data})" "\n"
        )