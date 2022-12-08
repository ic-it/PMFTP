import os
import time
import logging
import socket

from time import sleep
from threading import Thread
from protocol.socket import Socket
from protocol.connection import Connection
from protocol.types.conn_side import ConnSide

logging.basicConfig(level=logging.INFO)

UDP_IP = socket.gethostbyname(socket.gethostname())
UDP_PORT = None
RECVS_DIR = "recvs"


print(f"IP: {UDP_IP}")

if not os.path.exists(RECVS_DIR):
    os.mkdir(RECVS_DIR)

while not UDP_PORT:
    try:
        UDP_PORT = int(input("Enter port (5005): ") or 5005)
    except ValueError:
        UDP_PORT = None

sock = Socket(UDP_IP, UDP_PORT)

@sock.on_connect
def on_connect(conn: Connection):
    print("\r\nConnected handler", conn.other_side)


@sock.on_message
def on_message(conn: Connection, message: bytes):
    print(f"\r\nMessage: {message.decode('utf-8')} from {conn.other_side}")

@sock.on_file
def on_file(conn: Connection, file, filename: str):
    file.seek(0)

    if '/' in filename:
        filename = filename.replace('/', '_')
    
    while filename.startswith('.'):
        filename = filename.replace('.', '', 1)
    
    
    file_path = f"./{RECVS_DIR}/{filename}"
    file_path = os.path.abspath(file_path)

    with open(file_path, "wb") as f:
        f.write(file.read())
    
    print(f"\r\nFile {file_path}")


@sock.on_disconnect
def on_disconnect(conn: Connection):
    print("\r\nDisconnected handler", conn.other_side)



sock.bind()


def commandline(sock_: Socket):
    conn = None
    while True:
        command = input("Enter command (sendfile/sendmsg, connect, connections, exit, swith): ").strip()

        if command.startswith("switch"):
            ip, port = command.split(" ")[1].split(":")
            new_conn = filter(lambda x: x.other_side == ConnSide(ip, int(port)), sock_._connections)
            new_conn = list(new_conn)
            if len(new_conn) == 0:
                print("No connection found")
                continue
            conn = new_conn
        if command == "connections":
            for conn in sock_._connections:
                print(conn.other_side)
        elif command.startswith("connect"):
            command, side = command.split(" ", 1)
            ip, port = side.split(":")
            side = ConnSide(ip, int(port))
            conn = sock_.connect(side)
            print(f"Connected to {side}")
        elif command.startswith("sendfile"):
            if conn:
                conn.send_file(open(command.split(" ")[1], "rb"))
            else:
                print("You need to connect first")
        elif command.startswith("sendmsg"):
            if conn:
                conn.send_message(command.split(" ", 1)[1].encode("utf-8"))
            else:
                print("You need to connect first")
        elif command == "exit":
            sock_.unbind()
            break
        else:
            print("Unknown command")


Thread(target=commandline, args=(sock, )).start()

try:
    sock.listen()
except KeyboardInterrupt:
    print("Keyboard interrupt")

sock.unbind()