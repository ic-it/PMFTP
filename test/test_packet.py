from protocol.types.packets.syn_send_file import SynSendFilePacket
from protocol.types.header import Header

packet = SynSendFilePacket(header=Header())

print(packet.data)

packet.data_len = 12312312

print(packet.data)

packet.filename = "test"

print(packet.data)

print(packet.filename)
print(packet.data_len)