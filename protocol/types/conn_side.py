

class ConnSide:
    def __init__(self, ip: str, port: int) -> None:
        self._ip = 0b0
        self._port = port

        for part in ip.split('.'):
            self._ip += int(part)
            self._ip <<= 8
    
    @property
    def port(self) -> int:
        return self._port
    
    @property
    def ip(self):
        list_ip = []
        for i in range(4):
            list_ip.append(str(self._ip >> (8 * (4 - i)) & 0b11111111))
        return '.'.join(list_ip)
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConnSide):
            return NotImplemented
        return self.ip == other.ip and self.port == other.port

    def __str__(self) -> str:
        return f"{self.ip}:{self.port}"