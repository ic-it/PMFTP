from random import randint
import socket
import logging
import time

from selectors import DefaultSelector, EVENT_READ, EVENT_WRITE
from typing import Generator, Callable

from protocol.types.keychain import Keychain
from .types.iteration_status import IterationStatus
from .types.conn_side import ConnSide
from .utils import genereate_keys
from .connection import Connection
from .types.handlers import Handlers

LOG = logging.getLogger("Socket")

class Socket:
    def __init__(self, ip: str, port: int) -> None:
        self._bound_on: ConnSide = ConnSide(ip, port)
        self._keychain: Keychain = Keychain(*genereate_keys())
        self._socket: socket = None
        self._socket_selector: DefaultSelector = None

        self._iterators_queue: list[Callable] = []
        self._connections: list[Connection] = []
        self._handlers: Handlers = Handlers()

        self.emulate_problems = False
    
    @property
    def bound_on(self) -> ConnSide:
        return self._bound_on
    
    @property
    def is_bound(self) -> bool:
        return self._socket is not None
    
    @property
    def connections(self) -> list[Connection]:
        return self._connections
    
    def on_connect(self, func: Callable) -> Callable:
        self._handlers.on_connect = func
        return func
    
    def on_message(self, func: Callable) -> Callable:
        self._handlers.on_message = func
        return func
    
    def on_file(self, func: Callable) -> Callable:
        self._handlers.on_file = func
        return func
    
    def on_disconnect(self, func: Callable) -> Callable:
        self._handlers.on_disconnect = func
        return func

    def get_connection_by_side(self, side: ConnSide) -> Connection:
        for conn in self._connections:
            if conn.other_side == side:
                return conn
        return None
    
    def _iterate(self):
        if self._socket is None:
            LOG.warning("Socket not bound")
            return IterationStatus.FINISHED
        
        for key, _ in self._socket_selector.select(timeout=0):
            try:
                data, (ip, port) = key.fileobj.recvfrom(1024)
            except ConnectionResetError:
                LOG.warning("Connection reset")
                continue
            side = ConnSide(ip, port)
            LOG.debug(f"Received {len(data)} bytes from {side}")

            connection = self.get_connection_by_side(side)

            if not connection:
                connection = Connection(side, 
                                        self._keychain.copy(),
                                        self._send_to,
                                        self._handlers)
                connection._add_iterator = self._add_iterator
                self._add_iterator(connection._iterate)
                self._connections.append(connection)
        
            connection._recv(data)
        return IterationStatus.SLEEP
    
    def _send_to(self, side: ConnSide, data: bytes) -> None:
        if self.emulate_problems and randint(0, 1000) < 5:
            change_index = randint(0, len(data) - 1)
            data = data[:change_index] + bytes([randint(0, 255)]) + data[change_index + 1:]
        self._socket.sendto(data, (side.ip, side.port))
        LOG.debug(f"Sent {len(data)} bytes to {side}")
    
    def _add_iterator(self, iterable: Generator) -> None:
        self._iterators_queue.append(iterable)
    
    def bind(self) -> None:
        if self._socket is not None:
            LOG.warning("Socket already bound")
            return
        
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind((self._bound_on.ip, self._bound_on.port))
        self._socket.setblocking(False)

        self._socket_selector = DefaultSelector()
        self._socket_selector.register(self._socket, EVENT_READ)

        self._iterators_queue = []
        self._connections = []

        self._add_iterator(self._iterate)

        LOG.info(f"Socket bound on {self._bound_on}")
    
    def connect(self, side: ConnSide) -> Connection:
        for connection in self._connections:
            if connection.other_side == side:
                return connection
        
        connection = Connection(side, 
                                self._keychain.copy(),
                                self._send_to,
                                self._handlers)
        connection._add_iterator = self._add_iterator
        self._connections.append(connection)
        self._add_iterator(connection._iterate)
        connection.connect()
        
        return connection

    def clear_connections(self) -> None:
        for conn in self._connections:
            if conn.conversation_status.is_disconnected:
                LOG.debug(f"Accepted headers size (with {conn.other_side}): {conn._size_of_accepted_headers} bytes")
                self._connections.remove(conn)

    def disconnect(self, side: ConnSide) -> None:
        for conn in self._connections:
            if conn.other_side == side:
                conn.disconnect()
                self.clear_connections()
                break
    
    def disconnect_all(self) -> None:
        for conn in self._connections:
            conn.disconnect()
    
    def iterate_loop(self) -> None:
        if self._socket is None:
            LOG.warning("Socket not bound")
            return

        for iterator in self._iterators_queue:
            for i in range(40):
                status = iterator()
                if status == IterationStatus.FINISHED:
                    if iterator in self._iterators_queue:
                        self._iterators_queue.remove(iterator)
                    self.clear_connections()
                    break
                elif status == IterationStatus.SLEEP:
                    break
                elif status == IterationStatus.BUSY:
                    continue

    def listen(self) -> None:
        while self.is_bound:
            if int(time.time()) % 10 == 0:
                self.clear_connections()
            self.iterate_loop()
    
    def unbind(self) -> None:
        if self._socket is None:
            LOG.warning("Socket already unbound")
            return
        
        for conn in self._connections:
            conn.disconnect()
        
        self._socket.close()
        self._socket = None
        self._iterators_queue = []
        self._connections = []
        LOG.info(f"Socket unbound on {self._bound_on}")
    
    def __enter__(self) -> "Socket":
        self.bind()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.unbind()
