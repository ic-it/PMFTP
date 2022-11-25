import logging 

from protocol.socket import Socket

logging.basicConfig(level=logging.DEBUG)

UDP_IP = "127.0.0.1"
UDP_PORT = 5005

with Socket(UDP_IP, UDP_PORT) as main_loop:
    main_loop.listen()