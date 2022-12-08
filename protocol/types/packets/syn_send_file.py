from .base import Packet
from ..flags import Flags

class SynSendFilePacket(Packet):
    def _post_init_(self, *args, **kwargs) -> None:
        self.header.flags = Flags.SYN | Flags.SEND | Flags.FILE
        self.data = b'\x00\x00\x00\x00'

    @property
    def data_len(self) -> int:
        return int.from_bytes(self.data[:4], byteorder='big')

    @data_len.setter
    def data_len(self, data_len: int) -> None:
        self.data = data_len.to_bytes(4, byteorder='big') + self.data[4:]
    
    @property
    def filename(self) -> str:
        return self.data[4:].decode()
    
    @filename.setter
    def filename(self, filename: str) -> None:
        self.data = self.data_len.to_bytes(4, byteorder='big') + filename.encode()
    
    def __repr__(self) -> str:
        return super().__repr__() + f", data_len={self.data_len})"