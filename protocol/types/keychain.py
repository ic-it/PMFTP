from dataclasses import dataclass
from ..utils import PUBLIC_KEY_T, PRIVATE_KEY_T

@dataclass
class Keychain:
    public_key: PUBLIC_KEY_T
    private_key: PRIVATE_KEY_T
    other_public_key: PUBLIC_KEY_T = None

    def __copy__(self) -> 'Keychain':
        return Keychain(self.public_key, self.private_key, self.other_public_key)
    
    def copy(self) -> 'Keychain':
        return self.__copy__()