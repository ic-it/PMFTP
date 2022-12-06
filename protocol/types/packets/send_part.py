from .base import Packet
from ..flags import Flags

class SendPartPacket(Packet):
    def _post_init_(self, *args, **kwargs) -> None:
        self._auto_encrypt_decrypt = True
        self.header.flags = Flags.SEND | Flags.PART
        self.data = 0 .to_bytes(4, 'big') + b''
    
    @property
    def insertion_point(self) -> int:
        return int.from_bytes(self.data[:4], 'big')
    
    @insertion_point.setter
    def insertion_point(self, point: int) -> None:
        self.data = point.to_bytes(4, 'big') + self.data[4:]
    
    @property
    def data_part(self) -> bytes:
        return self.data[4:]
    
    @data_part.setter
    def data_part(self, data: bytes) -> None:
        self.data = self.data[:4] + data