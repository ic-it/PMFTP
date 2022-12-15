import os
import sys
import logging


from io import FileIO
from time import sleep
from threading import Thread
from typing import Callable
from protocol.socket import Socket
from protocol.connection import Connection
from protocol.types.conn_side import ConnSide
from protocol.transfers.send import SendTransfer
from protocol.transfers.recv import RecvTransfer



def validate_command(command: str, validate: list[Callable[[str], bool]]) -> bool:
    for validator in validate:
        if not validator(command):
            return False
    return True


def command_count_validator(count: int, more_less_eq: int = 0) -> bool:
    def validator(command: str):
        if more_less_eq == 0:
            return len(command.split(" ")) == count
        elif more_less_eq == 1:
            return len(command.split(" ")) >= count
        elif more_less_eq == -1:
            return len(command.split(" ")) <= count
    return validator

def command_startswith_validator(startswith: str) -> bool:
    def validator(command: str):
        return command.startswith(startswith)
    return validator


def commandline(sock_: Socket):
    conn_ = None
    fragment_size = None

    while True:
        if conn_:
            progresses = []
            for tid, (transfer, tio) in conn_.transfers.items():
                transfer: SendTransfer | RecvTransfer
                progresses.append(f"{transfer.filename}{ '->' if isinstance(transfer, SendTransfer) else '<-' }{transfer.progress:.2f}%")
            if len(progresses) > 0:
                send_in_s, recv_in_s = sock_.speed
                print(f"({', '.join(progresses)}) Send: {send_in_s}B/s Recv: {recv_in_s}B/s")

        try:
            command = input(f"[{sock_.bound_on}]>> ").strip()
        except EOFError:
            print()
            sys.stdin = open("/dev/tty")
        except KeyboardInterrupt:
            sock_.close()
            print('Closing socket')
            return
    
        if command_startswith_validator("help")(command):
            print("connect <ip:port> - connect to ip:port")
            print("disconnect - disconnect from current connection")
            print("connections - list all connections")
            print("switch <ip:port> - switch to connection")
            print("sendfile <file> - send file")
            print("sendmsg <message> - send message")
            print("fragment <size> - set fragment size")
            print("logging <level> - set logging level")
            print("help - show this message")
            print("exit - exit")

        if command_startswith_validator("switch")(command) and command_count_validator(2)(command):
            command, side = command.split(" ", 1)
            
            
            ip, port = side.split(":")
            
            new_conn = filter(lambda x: x.other_side == ConnSide(ip, int(port)), sock_._connections)
            new_conn = list(new_conn)
            if len(new_conn) == 0:
                print("No connection found")
                continue
            conn_ = new_conn
            continue
        
        if command_startswith_validator("connections")(command) and command_count_validator(1)(command):
            for conn_ in sock_._connections:
                print(conn_.other_side)
            continue
        
        if command_startswith_validator("connect")(command) and command_count_validator(2)(command):
            command, side = command.split(" ", 1)
            ip, port = side.split(":")
            side = ConnSide(ip, int(port))
            conn_ = sock_.connect(side)
            while not conn_.conversation_status.is_connected:
                sleep(0.1)
            print(f"Connected to {side}")
            continue
        
        if command_startswith_validator("disconnect")(command) and command_count_validator(1)(command):
            if conn_:
                sock_.disconnect(conn_.other_side)
                conn_ = None
            else:
                print("You need to connect first")
            continue
        
        if command_startswith_validator("sendfile")(command) and command_count_validator(2)(command):
            if conn_:
                command, path = command.split(" ", 1)
                if not os.path.exists(path):
                    print("File not found")
                    continue
                if not os.path.isfile(path):
                    print("Not a file")
                    continue
                try:
                    conn_.send_file(open(path, "rb"), fragment_size=fragment_size)
                except ValueError as e:
                    print(e)
            else:
                print("You need to connect first")
            continue
        
        if command_startswith_validator("sendmsg")(command) and command_count_validator(2, 1)(command):
            command, message = command.split(" ", 1)
            if conn_:
                conn_.send_message(message.encode("utf-8"), fragment_size=fragment_size)
            else:
                print("You need to connect first")
            continue
        
        if command_startswith_validator("fragment")(command) and command_count_validator(2)(command):
            command, fragment_size_ = command.split(" ", 1)
            if not fragment_size_.isnumeric():
                print("Invalid fragment size")
                fragment_size_ = None
                continue
            
            fragment_size = int(fragment_size_)
            
            continue
            
        if command_startswith_validator("logging")(command) and command_count_validator(2)(command):
            command, level = command.split(" ", 1)
            level = level.upper()
            if not level in logging._nameToLevel:
                print("Invalid logging level")
                logging.basicConfig(level=logging.NOTSET)
                continue
            
            logging.basicConfig(level=logging._nameToLevel[level])
            continue
        
        if command == "exit":
            sock_.disconnect_all()
            while len(sock_._connections) > 0:
                sleep(0.1)
            sock_.unbind()
            break
        
        if command == "":
            continue
        
        print("Unknown command")