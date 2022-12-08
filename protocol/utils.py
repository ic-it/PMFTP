import random

from typing import Type


PUBLIC_KEY_T = Type[int]
PRIVATE_KEY_T = Type[int]

def genereate_keys() -> tuple[int, int]:
    private_key = random.randint(0, 100)
    public_key = private_key * 2
    return public_key, private_key

def encrypt(data: bytes, public_key: int) -> bytes:
    return bytes([data[i] ^ public_key for i in range(len(data))])

def decrypt(data: bytes, private_key: int) -> bytes:
    return bytes([data[i] ^ (private_key * 2) for i in range(len(data))])

def decode_pubkey(pubkey: bytes) -> PUBLIC_KEY_T:
    return int.from_bytes(pubkey, byteorder='big')

def encode_pubkey(pubkey: PUBLIC_KEY_T) -> bytes:
    return pubkey.to_bytes(32, byteorder='big')


# def encrypt(data: bytes, public_key: int) -> bytes:
#     return data

# def decrypt(data: bytes, private_key: int) -> bytes:
#     return data



def seq_num_generator():
    seq_num = 0
    while True:
        yield seq_num
        seq_num += 1