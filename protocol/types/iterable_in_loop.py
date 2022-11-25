from typing import Generator
from .iteration_status import IterationStatus

class IterableInLoop:
    def iterator(self) -> Generator[IterationStatus, None, None]: ...