from io import FileIO
import os
import sys
import time
import logging
import socket

from time import sleep
from threading import Thread
from protocol.socket import Socket
from protocol.connection import Connection
from protocol.types.conn_side import ConnSide
from protocol.transfers.send import SendTransfer
from protocol.transfers.recv import RecvTransfer

# logging.basicConfig(level=logging.INFO)

_, _, ips = socket.gethostbyname_ex(socket.gethostname())

print("Select IP:")
for i, my_ip in enumerate(ips):
    print(f"{i}) {my_ip}")

ip_index = -1
while ip_index not in range(len(ips)):
    try:
        ip_index = int(input("Enter number: ") or 0)
    except ValueError:
        print("Invalid number")
    if ip_index not in range(len(ips)):
        print("Number out of range")
    
UDP_IP = ips[ip_index]
UDP_PORT = None
RECVS_DIR = "recvs"

console_width = os.get_terminal_size().columns
console_height = os.get_terminal_size().lines

def gotoxy(x,y):
    print("%c[%d;%df" % (0x1B, y, x), end='')



print(f"IP: {UDP_IP}")

if not os.path.exists(RECVS_DIR):
    os.mkdir(RECVS_DIR)

while not UDP_PORT:
    try:
        UDP_PORT = int(input("Enter port (5005): ") or 5005)
    except ValueError:
        UDP_PORT = None

sock = Socket(UDP_IP, UDP_PORT)

# sock.emulate_problems = True

@sock.on_connect
def on_connect(conn: Connection):
    print("\nConnected handler", conn.other_side)

@sock.on_message_recv
def on_message_recv(conn: Connection, message: bytes, is_correct: bool):
    print(f"\n({conn.other_side}, {is_correct=})<< {message.decode('utf-8')}")

@sock.on_message_send
def on_message_send(conn: Connection, message: bytes, is_correct: bool):
    print(f"\n({conn.other_side}, {is_correct=})>> {message.decode('utf-8')}")


@sock.on_file_recv
def on_file(conn: Connection, file: FileIO, filename: str, is_correct: bool):
    file.seek(0)

    if '/' in filename:
        filename = filename.replace('/', '_')
    
    while filename.startswith('.'):
        filename = filename.replace('.', '', 1)
    
    
    file_path = f"./{RECVS_DIR}/{filename}"
    if os.path.exists(file_path):
        file_path = f"./{RECVS_DIR}/{time.time()}_{filename}"
    file_path = os.path.abspath(file_path)

    with open(file_path, "wb") as f:
        f.write(file.read())
    
    print(f"\nFile {file_path} size: {os.path.getsize(file_path)} from {conn.other_side} is correct: {is_correct}")

@sock.on_file_send
def on_file_send(conn: Connection, file: FileIO, filename: str, is_correct: bool):
    print(f"\nFile {filename} size: {os.path.getsize(filename)} to {conn.other_side} is correct: {is_correct}")


@sock.on_disconnect
def on_disconnect(conn: Connection):
    print("\nDisconnected handler", conn.other_side)


sock.bind()


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

        if command == "help":
            print("connect <ip:port> - connect to ip:port")
            print("connections - list all connections")
            print("switch <ip:port> - switch to connection")
            print("sendfile <file> - send file")
            print("sendmsg <message> - send message")
            print("fragment <size> - set fragment size")
            print("help - show this message")
            print("exit - exit")
        
        if command.startswith("switch"):
            ip, port = command.split(" ")[1].split(":")
            new_conn = filter(lambda x: x.other_side == ConnSide(ip, int(port)), sock_._connections)
            new_conn = list(new_conn)
            if len(new_conn) == 0:
                print("No connection found")
                continue
            conn_ = new_conn
            continue
            
        if command == "connections":
            for conn_ in sock_._connections:
                print(conn_.other_side)
            continue
        
        if command.startswith("connect"):
            command, side = command.split(" ", 1)
            ip, port = side.split(":")
            side = ConnSide(ip, int(port))
            conn_ = sock_.connect(side)
            while not conn_.conversation_status.is_connected:
                sleep(0.1)
            print(f"Connected to {side}")
            continue
        
        if command.startswith("sendfile"):
            if conn_:
                fragment_size = None
                if len(command.split(" ")) == 3:
                    fragment_size = int(command.split(" ")[2])
                try:
                    conn_.send_file(open(command.split(" ")[1], "rb"), fragment_size=fragment_size)
                except ValueError as e:
                    print(e)
            else:
                print("You need to connect first")
            continue
        
        if command.startswith("sendmsg"):
            command = command.replace("sendmsg ", "")
            if conn_:
                msg = command
                conn_.send_message(msg.encode("utf-8"), fragment_size=fragment_size)
            else:
                print("You need to connect first")
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

Thread(target=commandline, args=(sock, )).start()

try:
    sock.listen()
except KeyboardInterrupt:
    print("Keyboard interrupt")

sock.unbind()