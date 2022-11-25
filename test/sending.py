import logging
import time

from protocol.socket import Socket 
from protocol.types.conn_side import ConnSide

logging.basicConfig(level=logging.DEBUG)


UDP_IP = "127.0.0.1"
UDP_PORT = 5006

with Socket(UDP_IP, UDP_PORT) as socket:
    conn = socket.connect(
        ConnSide(UDP_IP, 5005)
    )
    # socket.listen()

    for i in range(20):
        socket.iter_loop()
        time.sleep(0.1)
    
    conn.send_message(b"Hello, World!")

    for i in range(20):
        socket.iter_loop()
        time.sleep(0.1)

    conn.disconnect()