from .base import Packet
from ...utils import decode_pubkey, encode_pubkey, PUBLIC_KEY_T

class SynPacket(Packet):
    def _post_init_(self):
        if self.data == b'':
            self.data = 0 .to_bytes(32, byteorder='big') + 0 .to_bytes(2, byteorder='big')

    @property
    def data_public_key(self) -> PUBLIC_KEY_T:
        return decode_pubkey(self.data[0:32])
    
    @data_public_key.setter
    def data_public_key(self, public_key: PUBLIC_KEY_T) -> None:
        self.data = encode_pubkey(public_key) + self.data[32:]

    @property
    def window_size(self) -> int:
        return int.from_bytes(self.data[32:34], byteorder='big')
    
    @window_size.setter
    def window_size(self, window_size: int) -> None:
        self.data = self.data[0:32] + window_size.to_bytes(2, byteorder='big')
    
    def __repr__(self) -> str:
        return super().__repr__() + f'[public_key={self.data_public_key}, window_size={self.window_size}]'