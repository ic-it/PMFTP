from time import sleep
from threading import Thread

inp_queue: list[str] = []


def reader(inp_queue_: list[str]):
    while True:
        data = input()
        inp_queue_.append(data)


def writer(inp_queue_: list[str]):
    while True:
        while len(inp_queue_) > 0:
            data = inp_queue_.pop()
            print(f"reader: {data}")
        sleep(0.1)


Thread(target=reader, args=(inp_queue,)).start()

writer(inp_queue)