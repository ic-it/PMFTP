from .base import Packet
from ..flags import Flags

class SynSendMsgPacket(Packet):
    def _post_init_(self, *args, **kwargs) -> None:
        self.header.flags = Flags.SYN | Flags.SEND | Flags.MSG

    @property
    def message_len(self) -> int:
        return int.from_bytes(self.data[0:4], byteorder='big')

    @message_len.setter
    def message_len(self, message_len: int) -> None:
        self.data = message_len.to_bytes(4, byteorder='big')
    
    def __repr__(self) -> str:
        return super().__repr__() + f", message_len={self.message_len})"