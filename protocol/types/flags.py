from enum import IntFlag

class Flags(IntFlag):
    SYN     = 0b10000000
    ACK     = 0b01000000
    UNACK   = 0b00100000
    FIN     = 0b00010000
    SEND    = 0b00001000
    PART    = 0b00000100
    MSG     = 0b00000010
    FILE    = 0b00000001