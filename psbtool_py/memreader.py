import struct

class MemoryReader:
    def __init__(self, data):
        self.data = data
        self.position = 0

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        del self.data

    def seek(self, position, mode=0):
        if mode == 0:
            self.position = position
        elif mode == 1:
            self.position += position
        elif mode == 2:
            self.position = len(self.data) - position

    def read_byte(self):
        value = self.data[self.position]
        self.position += 1
        return value

    def read_bytes(self, length):
        value = self.data[self.position:self.position+length]
        self.position += length
        return value

    def read_uint32(self):
        value = struct.unpack("<I", self.data[self.position:self.position+4])[0]
        self.position += 4
        return value

    def read_cstring(self):
        base_pos = self.position
        while self.data[self.position] != 0 and self.position < len(self.data):
            self.position += 1
        self.position += 1
        return bytearray(self.data[base_pos:self.position-1]).decode("utf-8", "unicodeescape")