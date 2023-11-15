import struct
import zlib
from .memreader import MemoryReader
from .psbtype import PSB_MDF_SIGNATURE, PSB_SIGNATURE, PackageStatus, PSBType
from .algorithms import PSBHeader

class PSBStrMan:
    def __init__(self, script):
        self.script = bytearray(script)
        self.compressed_package = False # True
        self.compression_level = 9
        self.force_max_offset_length = False
        self.off_length = 0
        self.str_count = 0
        self.old_off_tbl_len = 0
        self.old_str_dat_len = 0
        self.header = None

    def import_strings(self):
        status = self.get_package_status(self.script)
        if status == PackageStatus.Invalid:
            raise Exception("Invalid Package")
        elif status == PackageStatus.MDF:
            self.script = self.extract_mdf(self.script)
            self.compressed_package = False #True

        with MemoryReader(self.script) as reader:
            self.header = PSBHeader()
            self.header.read_from_stream(reader)

            reader.seek(self.header.str_off_pos)
            size_type = reader.read_byte()
            self.count_length = self.convert_size(size_type)
            offsets = reader.read_bytes(self.count_length)
            self.str_count = self.read_offset(offsets, 0, self.count_length)

            length_type = reader.read_byte()
            self.off_length = self.convert_size(length_type)
            offsets = []
            for _ in range(self.str_count):
                offset_i = reader.read_bytes(self.off_length)
                offsets.append(self.read_offset(offset_i, 0, self.off_length))

            self.old_off_tbl_len = reader.position - self.header.str_off_pos

            strings = []
            reader.seek(self.header.str_data_pos)
            for offset in offsets:
                reader.seek(self.header.str_data_pos + offset)
                strings.append(reader.read_cstring())

            self.old_str_dat_len = reader.position - self.header.str_data_pos

        return strings

    def export_strings(self, strings):
        if len(strings) != self.str_count:
            raise Exception("Strings number must be consistent with the original")

        string_data, offsets = self.build_string_data(strings)
        offset_data = self.build_offset_table(offsets)

        off_tbl_diff = len(offset_data) - self.old_off_tbl_len
        str_dat_diff = len(string_data) - self.old_str_dat_len

        header = self.header
        header = self.update_offsets(header, off_tbl_diff, str_dat_diff)

        out_script = bytearray(self.script)
        out_script = self.overwrite_range(out_script, header.str_off_pos, self.old_off_tbl_len, offset_data)
        out_script = self.overwrite_range(out_script, header.str_data_pos, self.old_str_dat_len, string_data)

        header_bytes = header.to_bytes()
        out_script[:len(header_bytes)] = header_bytes

        return zlib.compress(out_script, self.compression_level) if self.compressed_package else out_script

    def overwrite_range(self, original_data, start, length, data_to_overwrite):
        return original_data[:start] + data_to_overwrite + original_data[start + length:]

    def update_offsets(self, header, off_tbl_diff, str_dat_diff):
        header.res_off_pos = self.update_offset(header.res_off_pos, header.str_off_pos, off_tbl_diff)
        header.res_data_pos = self.update_offset(header.res_data_pos, header.str_off_pos, off_tbl_diff)
        header.res_len_pos = self.update_offset(header.res_len_pos, header.str_off_pos, off_tbl_diff)
        header.res_index_tree = self.update_offset(header.res_index_tree, header.str_off_pos, off_tbl_diff)
        header.str_data_pos = self.update_offset(header.str_data_pos, header.str_off_pos, off_tbl_diff)

        header.res_off_pos = self.update_offset(header.res_off_pos, header.str_data_pos, str_dat_diff)
        header.res_data_pos = self.update_offset(header.res_data_pos, header.str_data_pos, str_dat_diff)
        header.res_len_pos = self.update_offset(header.res_len_pos, header.str_data_pos, str_dat_diff)
        header.res_index_tree = self.update_offset(header.res_index_tree, header.str_data_pos, str_dat_diff)
        return header

    @staticmethod
    def update_offset(offset, change_base_offset, diff):
        if offset < change_base_offset:
            return offset
        return offset + diff

    def build_string_data(self, strings):
        offsets = []
        string_data = bytearray()

        for string in strings:
            offsets.append(len(string_data))
            string_data.extend(string.encode("utf-8") + b'\0')

        return string_data, offsets

    def build_offset_table(self, offsets):
        offset_data = bytearray()

        offset_size = 4 if self.force_max_offset_length else self.get_min_int_len(self.str_count)
        offset_data.append(self.unconvert_size(offset_size))
        offset_data.extend(self.create_offset(offset_size, self.str_count))

        offset_size = 4 if self.force_max_offset_length else self.get_min_int_len(offsets[-1])
        offset_data.append(self.unconvert_size(offset_size))

        for offset in offsets:
            offset_data.extend(self.create_offset(offset_size, offset))

        return offset_data

    @staticmethod
    def compress_mdf(psb):
        compressed_script = zlib.compress(psb)
        ret_data = bytearray('')
        ret_data.extend(struct.pack("<I", len(psb)))
        ret_data.extend(compressed_script)
        return ret_data

    def try_recovery(self):
        script = bytearray(self.script)
        status = self.get_package_status(script)
        if status == PackageStatus.Invalid:
            raise Exception("Invalid package")
        mdf = status == PackageStatus.MDF
        if mdf:
            script = self.extract_mdf(script)

        str_off = self.read_offset(script, 0x10, 4)
        str_data = self.read_offset(script, 0x14, 4)
        cnt_size = self.convert_size(script[str_off])
        count = self.read_offset(script, str_off + 1, cnt_size)
        size = self.convert_size(script[str_off + 1 + cnt_size])
        end_str = (str_off + 2 + cnt_size) + ((count - 1) * size)
        end_str = self.read_offset(script, end_str, size) + str_data
        while script[end_str] != 0x00:
            end_str += 1

        seq = bytearray([0xD, 0x0, 0xD])
        if self.equals_at(script, seq, end_str + 1) and self.equals_at(script, seq, end_str + 1 + len(seq)):
            self.overwrite_range(script, 0x18, 4, self.create_offset(4, end_str + 1))
            self.overwrite_range(script, 0x1C, 4, self.create_offset(4, end_str + 4))
            self.overwrite_range(script, 0x20, 4, self.create_offset(4, end_str + 7))
            return self.compress_mdf(script) if mdf else script
        else:
            try:
                self.convert_size(script[self.read_offset(script, 0x18, 4)])
                self.convert_size(script[self.read_offset(script, 0x1C, 4)])
                return self.compress_mdf(script) if mdf else script
            except:
                raise Exception("You can't attempt recovery because this package contains data.")

    @staticmethod
    def equals_at(data, compare_data, pos):
        if len(compare_data) + pos > len(data):
            return False
        for i in range(len(compare_data)):
            if data[i + pos] != compare_data[i]:
                return False
        return True

    @staticmethod
    def get_min_int_len(value):
        min_len = 0
        while value >> (min_len * 8) > 0:
            min_len += 1
        return min_len

    @staticmethod
    def create_offset(length, value: int):
        if value >= (length << 15):
            raise Exception(f"Offset {value} is too big for its byte size 2^({length} * 8)")
        return value.to_bytes(length, 'little')

    @staticmethod
    def convert_size(sz_val):
        size = sz_val - PSBType.INTEGER_ARRAY_N
        if 9 <= size <= 0:
            raise ValueError(f"{sz_val} is not an INTEGER_ARRAY_N")
        return size

    @staticmethod
    def unconvert_size(size):
        if size < 9:
            return PSBType.INTEGER_ARRAY_N + size
        raise ValueError("Arrays can have maximum 8 byte size")

    @staticmethod
    def read_offset(data, index, length):
        return int.from_bytes(data[index:index+length], 'little')

    @staticmethod
    def get_package_status(package):
        if package[:4] == PSB_MDF_SIGNATURE:
            return PackageStatus.MDF
        elif package[:4] == PSB_SIGNATURE:
            return PackageStatus.PSB
        return PackageStatus.Invalid
