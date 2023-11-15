import struct
import codecs
from io import IOBase, BytesIO

class Sector:
    def __init__(self, data, pos):
        data.seek(pos)
        self.type = data.read(4).decode('ascii')
        data_length = struct.unpack('<I', data.read(4))[0]
        self.content = data.read(data_length)
        self.full_length = data_length + 8

    def generate(self):
        sector = bytearray()
        sector.extend(self.type.encode('ascii'))
        sector.extend(struct.pack('<I', len(self.content)))
        sector.extend(self.content)
        return sector

def read_uint(data, pos):
    data.seek(pos)
    return struct.unpack('<I', data.read(4))[0]

def generate_uint(value):
    return struct.pack('<I', value)

def parse_tjs(tjs2: IOBase):
    tjs2_len = read_uint(tjs2, 8)
    tjs2.seek(0, 2)
    if tjs2_len != tjs2.tell():
        raise Exception("Corrupted or incompatible .tjs file")
    # first sector is data
    pointer = 12
    data = Sector(tjs2, pointer)
    pointer += data.full_length

    other = []
    other_length = read_uint(tjs2, pointer)
    pointer += 4
    for _ in range(other_length):
        sector = Sector(tjs2, pointer)
        pointer += sector.full_length
        other.append(sector)

    tjs = []
    tjs_length = read_uint(tjs2, pointer)
    pointer += 4
    for _ in range(tjs_length):
        sector = Sector(tjs2, pointer)
        pointer += sector.full_length
        tjs.append(sector)

    # merge sector arrays
    sectors = [data] + other + tjs
    return sectors

def merge_sectors(sectors):
    data = None
    other = []
    tjs = []
    for sector in sectors:
        if sector.type == "DATA":
            data = sector
        elif sector.type == "TJS2":
            tjs.append(sector)
        else:
            other.append(sector)

    # data segment and header
    out_tjs2 = bytearray()
    out_tjs2.extend(bytearray(b'TJS2100\0')) # signature & version
    out_tjs2.extend(b'\0\0\0\0') # file length placeholder
    out_tjs2.extend(data.generate())

    # other segments
    out_tjs2.extend(generate_uint(len(other)))
    for sector in other:
        out_tjs2.extend(sector.generate())

    # TJS2 segments
    out_tjs2.extend(generate_uint(len(tjs)))
    for sector in tjs:
        out_tjs2.extend(sector.generate())

    # fill the file length placeholder
    out_tjs2[0x08:0x0C] = generate_uint(len(out_tjs2))

    return out_tjs2

def get_strings(sector):
    if sector.type != "DATA":
        raise Exception("Sector Type Not Supported")
    data = BytesIO(sector.content)

    str_pos = find_string_pos(data)

    strings = []
    string_count = read_uint(data, str_pos)
    str_pos += 4
    for _ in range(string_count):
        string_length = read_uint(data, str_pos) * 2
        str_pos += 4
        string = codecs.decode(data.read(string_length), 'utf-16le')
        strings.append(string)
        str_pos += string_length
        str_pos = round_up(str_pos, 4)

    return strings

def set_strings(sector, strings):
    if sector.type != "DATA":
        raise Exception("Sector Type Not Supported")
    data = BytesIO(sector.content)

    # load positions
    str_pos = find_string_pos(data)
    end_pos = find_str_end(str_pos, data)

    # copy non-string data
    data.seek(0)
    values = data.read(str_pos)

    string_table = bytearray()
    string_table.extend(generate_uint(len(strings))) # String Count

    # generate string table
    for string in strings:
        string_length = round_up(len(string) * 2, 4)
        string_entry = bytearray()
        string_entry.extend(generate_uint(len(string)))
        new_str = codecs.encode(string, 'utf-16le')
        string_entry.extend(new_str)
        string_entry.extend((string_length - len(new_str)) * b'\0') # padding
        string_table.extend(string_entry)

    # copy object values
    data.seek(end_pos)
    objs = data.read()

    # generate sector content
    new_content = bytearray()
    new_content.extend(values)
    new_content.extend(string_table)
    new_content.extend(objs)

    # Return
    sector.content = bytes(new_content)

def append(data_table, data_to_append):
    return data_table + data_to_append

def append_sector(data_table, sector_to_append):
    return data_table + [sector_to_append]

def find_str_end(str_pos, data):
    count = read_uint(data, str_pos)
    str_pos += 4
    for _ in range(count):
        length = read_uint(data, str_pos)
        str_pos += 4 + round_up(length * 2, 4)
    return str_pos

def find_string_pos(data):
    str_pos = read_uint(data, 0) + 4 # skip 8 bits array
    str_pos = round_up(str_pos, 4)

    str_pos += (read_uint(data, str_pos) * 2) + 4 # skip 16 bits array
    str_pos = round_up(str_pos, 4)

    str_pos += (read_uint(data, str_pos) * 4) + 4 # skip 32 bits array
    str_pos = round_up(str_pos, 4)

    str_pos += (read_uint(data, str_pos) * 8) + 4 # skip 64 bits array
    str_pos = round_up(str_pos, 4)

    str_pos += (read_uint(data, str_pos) * 8) + 4 # skip 64 bits unknown (IEEE Float?)
    str_pos = round_up(str_pos, 4)

    return str_pos

def round_up(value, multiplier):
    while value % multiplier != 0:
        value += 1
    return value

class TJS2SManager:
    def __init__(self, script):
        self.sectors = parse_tjs(script)
        for i, sector in enumerate(self.sectors):
            if sector.type == "DATA":
                self.data_index = i
                return
        raise Exception("Failed to parse TJS file")

    def import_strings(self):
        return get_strings(self.sectors[self.data_index])

    def export_strings(self, strings):
        set_strings(self.sectors[self.data_index], strings)
        return merge_sectors(self.sectors)


if __name__ == '__main__':
    with open("YesNoDialog.tjs", "rb") as f:
        test = TJS2SManager(f)
        strs = test.import_strings()
        for i, s in enumerate(strs):
            if s == "はい":
                strs[i] = "Yes"
            elif s == "いいえ":
                strs[i]= "No"
        with open("out_YesNoDialog.tjs", "wb") as o:
            o.write(test.export_strings(strs))
        pass
