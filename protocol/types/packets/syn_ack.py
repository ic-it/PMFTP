from .syn import SynPacket
from ..flags import Flags

class SynAckPacket(SynPacket):
    def _post_init_(self):
        super()._post_init_()
        self.header.flags = Flags.SYN | Flags.ACK
