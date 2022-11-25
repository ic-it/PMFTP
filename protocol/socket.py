import socket
import logging
import time
from typing import Generator

from .iterators_queue import IteratorsQueue
from .types.iterable_in_loop import IterableInLoop
from .types.iteration_status import IterationStatus
from .types.conn_side import ConnSide
from .utils import PRIVATE_KEY_T, PUBLIC_KEY_T, genereate_keys
from .connection import Connection

LOG = logging.getLogger("main_loop")

class Socket:
    def __init__(self, ip: str, port: int) -> None:
        self._bound_on: ConnSide = ConnSide(ip, port)
        self._public_key: PUBLIC_KEY_T = None
        self._private_key: PRIVATE_KEY_T = None
        self._socket: socket = None
        self._iterators_queue: list[callable] = None
        self._connections: list[Connection] = None

        self._public_key, self._private_key = genereate_keys()
    
    @property
    def bound_on(self) -> ConnSide:
        return self._bound_on
    
    @property
    def is_bound(self) -> bool:
        return self._socket is not None
    
    def _recv_iter(self) -> IterableInLoop:
        try:
            data, (ip, port) = self._socket.recvfrom(1024)
            side = ConnSide(ip, port)
        except BlockingIOError:
            return IterationStatus.SLEEP
        
        connection = None
        for conn in self._connections:
            if conn.other_side == side:
                connection = conn
                break
        
        if not connection:
            connection = Connection(side, self._public_key, self._private_key, self._send_to)
            self._add_iterator(connection.process)
            self._connections.append(connection)
        
        connection.recv(data)
        
        return IterationStatus.SLEEP
    
    def _send_to(self, side: ConnSide, data: bytes) -> None:
        self._socket.sendto(data, (side.ip, side.port))
    
    def _add_iterator(self, iterable: Generator) -> None:
        self._iterators_queue.append(iterable)
    
    def bind(self) -> None:
        if self._socket is not None:
            LOG.warning("Socket already bound")
            return
        
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind((self._bound_on.ip, self._bound_on.port))
        self._socket.setblocking(False)

        self._iterators_queue = []
        self._connections = []

        self._add_iterator(self._recv_iter)

        LOG.debug(f"Socket bound on {self._bound_on}")
    
    def connect(self, side: ConnSide) -> Connection:
        for conn in self._connections:
            if conn.other_side == side:
                return conn
        
        conn = Connection(side, self._public_key, self._private_key, self._send_to)
        self._connections.append(conn)
        self._add_iterator(conn.process)
        conn.connect()
        return conn
    
    def clear_connections(self) -> None:
        for conn in self._connections:
            if conn._conversation_status.is_disconnected:
                self._connections.remove(conn)
                LOG.debug(f"Connection to {conn.other_side} finished")

    def disconnect(self, side: ConnSide) -> None:
        for conn in self._connections:
            if conn.other_side == side:
                conn.disconnect()
                self.clear_connections()
                break
    
    def iter_loop(self) -> None:
        if self._socket is None:
            LOG.warning("Socket not bound")
            return

        for item in self._iterators_queue:
            status = item()
            if status == IterationStatus.FINISHED:
                self._iterators_queue.remove(item)
                self.clear_connections()

    def listen(self) -> None:
        while self.is_bound:
            self.iter_loop()
            time.sleep(0.01)
    
    def unbind(self) -> None:
        if self._socket is None:
            LOG.warning("Socket already unbound")
            return
        
        self._socket.close()
        self._socket = None
        self._iterators_queue = None
        self._connections = None
        LOG.debug("Socket unbound")
    
    def __enter__(self) -> "Socket":
        self.bind()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.unbind()
