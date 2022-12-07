import logging
import time

from protocol.socket import Socket 
from protocol.types.conn_side import ConnSide

logging.basicConfig(level=logging.INFO)


UDP_IP = "127.0.0.1"
UDP_PORT = 5006

with Socket(UDP_IP, UDP_PORT) as socket:
    @socket.on_file
    def on_file(conn, file, filename: str):
        file.seek(0)

        if '/' in filename:
            filename = filename.replace('/', '\\')

        with open(f"SND{filename}", "wb") as f:
            f.write(file.read())
        
        print(f"File {filename}")

    
    conn = socket.connect(
        ConnSide(UDP_IP, 5005)
    )

    while not conn.conversation_status.is_connected and not conn.conversation_status.is_incorrect_disconnected:
        socket.iterate_loop()
        time.sleep(1)
    
    if conn.conversation_status.is_incorrect_disconnected:
        print("Connection failed")
        exit(1)
    
    trnsfer1 = conn.send_file(open("../IMG1.svg", "rb"))

    while not trnsfer1.done:
        socket.iterate_loop()
        print(f"Progress: {trnsfer1.progress: .2f}% {trnsfer1.window_fill}", end="\r")

        

    while conn.transfers_count:
        socket.iterate_loop()
        time.sleep(0.1)
    
    conn.disconnect()

    while not conn.conversation_status.is_disconnected:
        socket.iterate_loop()
        time.sleep(0.1)

    print(conn.conversation_status)
