from ctypes import c_uint32, c_uint16
from .flags import Flags

HEADER_SIZE = 13 # bytes

class Header:
    def __init__(self, seq_number: int = 0, ack_number: int = 0,
                flags: Flags = None, transfer_id: int = 0, checksum: int = 0) -> None:
        if flags is None:
            flags = Flags(0)
        self.__seq_number = c_uint32(seq_number)
        self.__ack_number = c_uint32(ack_number)
        self.__flags = flags
        self.__transfer_id = c_uint16(transfer_id)
        self.__checksum = c_uint16(checksum)
        
    @property
    def seq_number(self) -> int:
        return self.__seq_number.value
    
    @seq_number.setter
    def seq_number(self, seq_number: int) -> None:
        self.__seq_number = c_uint32(seq_number)
    
    @property
    def ack_number(self) -> int:
        return self.__ack_number.value

    @property
    def flags(self) -> Flags:
        return self.__flags
    
    @flags.setter
    def flags(self, flags: Flags) -> None:
        self.__flags = flags

    @property
    def transfer_id(self) -> int:
        return self.__transfer_id.value
    
    @transfer_id.setter
    def transfer_id(self, transfer_id: int) -> None:
        self.__transfer_id = c_uint16(transfer_id)

    @property
    def checksum(self) -> int:
        return self.__checksum.value

    @checksum.setter
    def checksum(self, checksum: int) -> None:
        self.__checksum = c_uint16(checksum)

    def dump(self) -> bytes:
        return (
            self.__seq_number.value.to_bytes(4, byteorder='big')
            + self.__ack_number.value.to_bytes(4, byteorder='big')
            + self.__flags.value.to_bytes(1, byteorder='big') 
            + self.__transfer_id.value.to_bytes(2, byteorder='big')
            + self.__checksum.value.to_bytes(2, byteorder='big')
        )
    
    def load(self, data: bytes) -> None:
        self.__seq_number = c_uint32(int.from_bytes(data[0:4], byteorder='big'))
        self.__ack_number = c_uint32(int.from_bytes(data[4:8], byteorder='big'))
        self.__flags = Flags(int.from_bytes(data[8:9], byteorder='big'))
        self.__transfer_id = c_uint16(int.from_bytes(data[9:11], byteorder='big'))
        self.__checksum = c_uint16(int.from_bytes(data[11:13], byteorder='big'))
    
    def __str__(self) -> str:
        return (
            f"Header(seq_number={self.__seq_number.value}, "
            f"ack_number={self.__ack_number.value}, "
            f"flags={self.__flags.__repr__()}, "
            f"__transfer_id={self.__transfer_id.value}, "
            f"checksum={self.__checksum.value})"
        )

    def __repr__(self) -> str:
        return self.__str__()