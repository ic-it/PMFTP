import os
import time
import socket

# import readline


from io import FileIO
from threading import Thread
from protocol.socket import Socket
from protocol.connection import Connection

from commandline import commandline

# Setup readline
complition_list = [
    "connect",
    "disconnect",
    "connections",
    "switch",
    "sendfile",
    "sendmsg",
    "fragment",
    "logging",
    "help",
    "exit",
]

def complition(text, state):
    options = [i for i in complition_list if i.startswith(text)]

    if state < len(options):
        return options[state]
    else:
        return None

# readline.parse_and_bind("tab: complete")
# readline.set_completer(complition)

# 

_, _, ips = socket.gethostbyname_ex(socket.gethostname())

print("Select IP:")
for i, my_ip in enumerate(ips):
    print(f"{i}) {my_ip}")

ip_index = -1
while ip_index not in range(len(ips)):
    try:
        ip_index = int(input("Enter number (0): ") or 0)
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

# get open port
s_ = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s_.bind((UDP_IP, 0))
default_port = s_.getsockname()[1]
s_.close()
default_port = int(default_port)

while not UDP_PORT:
    try:
        UDP_PORT = int(input(f"Enter port ({default_port}): ") or default_port)
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



Thread(target=commandline, args=(sock, )).start()

try:
    sock.listen()
except KeyboardInterrupt:
    print("Keyboard interrupt")

sock.unbind()