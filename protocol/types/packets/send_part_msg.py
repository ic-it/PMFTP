from .base import Packet
from .send_part import SendPartPacket
from ..flags import Flags


class SendPartMsgPacket(SendPartPacket):
    def _post_init_(self, *args, **kwargs) -> None:
        self._auto_encrypt_decrypt = True
        self.header.flags |= Flags.MSG

    @property
    def message(self) -> bytes:
        return self.data_part

    @message.setter
    def message(self, msg: bytes) -> None:
        self.data_part = msg

    def __repr__(self) -> str:
        return super().__repr__() + f", message={self.message})"