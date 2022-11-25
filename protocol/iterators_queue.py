from typing import Generator
from .types.iterable_in_loop import IterableInLoop
from .types.iteration_status import IterationStatus

class IteratorsQueue:
    def __init__(self):
        self.__queue: list[Generator[IterationStatus, None, None]] = []

    def push(self, item: IterableInLoop) -> None:
        self.__queue.append(item)

    def iterate(self) -> None:
        for item in self.__queue:
            status = item()
            if status == IterationStatus.FINISHED:
                self.__queue.remove(item)