from .base import Packet
from ..flags import Flags

class SendPartMsgPacket(Packet):
    def _post_init_(self, *args, **kwargs) -> None:
        self._auto_encrypt_decrypt = True
        self.header.flags |= Flags.SEND | Flags.PART | Flags.MSG

    @property
    def message(self) -> bytes:
        return self.data

    @message.setter
    def message(self, msg: bytes) -> None:
        self.data = msg
        
    
    def __repr__(self) -> str:
        return super().__repr__() + f", message={self.message})"