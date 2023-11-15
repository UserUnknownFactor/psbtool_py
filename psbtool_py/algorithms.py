import zlib
import struct
from .memreader import MemoryReader

def compress_data(in_data, compression):
    out_data = zlib.compress(in_data, compression)
    return out_data

def decompress_data(in_data):
    try:
        out_data = zlib.decompress(in_data)
        return out_data
    except:
        return b''

def read_c_string(stream, encoding=None):
    if encoding is None:
        encoding = 'utf-8'

    _buffer = bytearray()
    last_byte = stream.read(1)
    while last_byte != b'\0':
        if not last_byte:
            raise OverflowError("Internal _buffer overflow exception")
        _buffer.extend(last_byte)
        last_byte = stream.read(1)
    return _buffer.decode(encoding)

def write_c_string(stream, string, encoding=None):
    if encoding is None:
        encoding = 'utf-8'
    stream.write(string.encode(encoding) + b'\0')

def read_bytes(stream, count):
    _buffer = stream.read(count)
    if len(_buffer) != count:
        raise Exception("Buffer Overflow Exception")
    return _buffer

def write_bytes(stream, data):
    stream.write(data)

def read_struct(stream, struct_type):
    _buffer = stream.read(struct.calcsize(struct_type))
    return struct.unpack(struct_type, _buffer)

def write_struct(stream, struct_type, struct_data):
    _buffer = struct.pack(struct_type, *struct_data)
    stream.write(_buffer)

class PSBHeader:
    def __init__(self):
        self.signature = 0
        self.version = 0
        self.name_off_pos = 0
        self.name_data_pos = 0
        self.str_off_pos = 0
        self.str_data_pos = 0
        self.res_off_pos = 0
        self.res_len_pos = 0
        self.res_data_pos = 0
        self.res_index_tree = 0

    def read_from_stream(self, reader: MemoryReader):
        self.signature = reader.read_bytes(4)
        self.version = reader.read_uint32()
        self.name_off_pos = reader.read_uint32()
        self.name_data_pos = reader.read_uint32()
        self.str_off_pos = reader.read_uint32()
        self.str_data_pos = reader.read_uint32()
        self.res_off_pos = reader.read_uint32()
        self.res_data_pos = reader.read_uint32()
        self.res_len_pos = reader.read_uint32()
        self.res_index_tree = reader.read_uint32()

    @classmethod
    def from_bytes(cls, data):
        header = cls()
        header.signature,
        header.version,
        self.name_off_pos,
        self.name_data_pos,
        self.str_off_pos,
        self.str_data_pos,
        self.res_off_pos,
        self.res_data_pos,
        self.res_len_pos,
        header.res_index_tree = struct.unpack('<4sIIIIIIIII', data)
        return header

    def to_bytes(self):
        return struct.pack(
            '<4sIIIIIIIII',
            self.signature,
            self.version,
            self.name_off_pos,
            self.name_data_pos,
            self.str_off_pos,
            self.str_data_pos,
            self.res_off_pos,
            self.res_data_pos,
            self.res_len_pos,
            self.res_index_tree
        )