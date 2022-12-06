from enum import Enum


class IterationStatus(Enum):
    SLEEP: int = 0
    FINISHED: int = 1
    BUSY: int = 2