import logging

from io import BytesIO
from random import randint
import time
from protocol.connection import Connection 

from protocol.socket import Socket

logging.basicConfig(level=logging.INFO)

UDP_IP = "127.0.0.1"
UDP_PORT = 5005

socket = Socket(UDP_IP, UDP_PORT)

@socket.on_connect
def on_connect(conn: Connection):
    while not conn.conversation_status.is_connected and not conn.conversation_status.is_incorrect_disconnected:
        socket.iterate_loop()
        time.sleep(1)
    
    conn.send_file(open("../IMG2.svg", "rb"))
    print("Connected handler")


@socket.on_message
def on_message(conn: Connection, message: bytes):
    print(f"Message: {message.decode('utf-8')}")

@socket.on_file
def on_file(conn: Connection, file: BytesIO, filename: str):
    file.seek(0)

    if '/' in filename:
        filename = filename.replace('/', '\\')

    with open(f"RECV{filename}", "wb") as f:
        f.write(file.read())
    
    print(f"File {filename}")
    

@socket.on_disconnect
def on_disconnect(conn: Connection):
    print("Disconnected handler")


with socket as socket:
    socket.listen()

