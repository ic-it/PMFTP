from .base import Packet
from ..flags import Flags
from ...utils import decode_pubkey, encode_pubkey, PUBLIC_KEY_T

class SynPacket(Packet):
    def _post_init_(self):
        if self.data == b'':
            self.data = 0 .to_bytes(64, byteorder='big')
        
        self.header.flags = Flags.SYN

    @property
    def public_key(self) -> PUBLIC_KEY_T:
        return decode_pubkey(self.data[:64])
    
    @public_key.setter
    def public_key(self, public_key: PUBLIC_KEY_T) -> None:
        self.data = encode_pubkey(public_key)
    
    def __repr__(self) -> str:
        return super().__repr__() + f'[public_key={self.public_key}]'