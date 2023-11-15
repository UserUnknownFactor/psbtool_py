from .stringmanager import PSBStrMan, PackageStatus
from .psbtype import PSBType
from io import IOBase

class PSBAnalyzer:
    def __init__(self, script: bytes):
        self.warning = False
        self.embedded_reference = False
        self.extend_string_limit = False # True
        self.compress_package = False # True
        self.compression_level = 0 # 9
        self.byte_code_start = 0
        self.byte_code_len = 0
        self.strings = []
        self.script = script
        self.string_manager = None
        self.calls = []

        status = PSBStrMan.get_package_status(script)
        if status == PackageStatus.MDF:
            script = PSBStrMan.extract_MDF(script)
        elif status != PackageStatus.PSB:
            raise Exception("Unrecognized .psb file format")

        self.script = bytearray(script)
        self.string_manager = PSBStrMan(script)
        self.string_manager.compress_package = True
        self.string_manager.force_max_offset_length = self.extend_string_limit

        self.byte_code_start = self.read_offset(self.script, 0x24, 4)
        self.byte_code_len = self.read_offset(self.script, 0x10, 4) - self.byte_code_start

        if self.byte_code_len + self.byte_code_start > len(self.script):
            raise Exception(f"Corrupted or incompatible code")

    @property
    def unk_op_codes(self):
        return self.warning

    @property
    def have_embedded(self):
        return self.embedded_reference

    def import_strings(self):
        self.embedded_reference = False
        self.warning = False

        self.calls = []
        self.strings = self.string_manager.import_strings()
        index = self.byte_code_start
        while index < self.byte_code_len + self.byte_code_start:
            result, index = self.analyze(self.script, index)

            for string_id in result:
                if string_id < len(self.strings) and string_id not in self.calls:
                    self.calls.append(string_id)

        for i in range(len(self.strings)):
            if i not in self.calls:
                self.calls.append(i)

        return self.desort_strings(self.strings, self.calls)

    def export_strings(self, strings):
        content = self.sort_strings(strings, self.calls)

        self.string_manager.compress_package = self.compress_package
        PSBStrMan.compression_level = self.compression_level

        return self.string_manager.export_strings(content)

    def desort_strings(self, strings, mapping):
        if len(mapping) != len(strings):
            raise Exception(f"String calls count missmatch {len(mapping)} != {len(strings)}")

        result = [None] * len(strings)
        for i in range(len(mapping)):
            result[i] = strings[mapping[i]]

        return result

    def sort_strings(self, strings, mapping):
        if len(mapping) != len(strings):
            raise Exception(f"String calls count missmatch {len(mapping)} != {len(strings)}")

        result = [None] * len(strings)
        for i in range(len(mapping)):
            result[mapping[i]] = strings[i]

        return result

    def analyze(self, script, index):
        assert index > 0, "wrong index"
        ids = []
        value_type = script[index]
        #print(f"{hex(value_type).replace('0x', '').zfill(2)} ", end='')
        index += 1

        if PSBType.NONE <= value_type <= PSBType.TRUE:
            pass
        elif value_type == PSBType.LIST:
            result, index = self.analyze(script, index)
            ids.extend(result)
        elif value_type == PSBType.OBJECT:
            result, index = self.analyze(script, index)
            ids.extend(result)
            result, index = self.analyze(script, index)
            ids.extend(result)
        elif value_type > PSBType.STRING_N and value_type <= PSBType.STRING_N + 4:
            value_size = value_type - PSBType.STRING_N
            ids.append(self.read_offset(script, index, value_size))
            index += value_size
        elif value_type == PSBType.DOUBLE:
            index += 8
        elif value_type == PSBType.FLOAT0:
            pass
        elif value_type == PSBType.FLOAT:
            index += 4
        elif value_type >= PSBType.INTEGER_N and value_type <= PSBType.INTEGER_N + 8:
            index += value_type - PSBType.INTEGER_N
        elif value_type > PSBType.INTEGER_ARRAY_N and value_type <= PSBType.INTEGER_ARRAY_N + 8:
            clength = value_type - PSBType.INTEGER_ARRAY_N
            count = self.read_offset(script, index, clength)
            index += clength
            elength = script[index] - PSBType.INTEGER_ARRAY_N
            assert elength > 0, "wrong integer elength"
            index += 1 + elength * count
        elif value_type > PSBType.RESOURCE_N and value_type <= PSBType.RESOURCE_N + 4:
            index += 1
            self.embedded_reference = True
            index += value_type - PSBType.RESOURCE_N
            assert index > 0, "wrong resource index"
        elif value_type > PSBType.EXTRA_N and value_type <= PSBType.EXTRA_N + 4:
            index += value_type - PSBType.EXTRA_N
            assert index > 0, "wrong extra index"
        elif (value_type == PSBType.COMPILER_INTEGER or
            value_type == PSBType.COMPILER_STRING or
            value_type == PSBType.COMPILER_RESOURCE or
            value_type == PSBType.COMPILER_ARRAY or
            value_type == PSBType.COMPILER_BOOL or
            value_type == PSBType.COMPILER_BINARY_TREE):
            pass
        else:
            self.warning = True
            raise ValueError(f"Invalid PSB value: {hex(value_type).zfill(2)}")
        return ids, index

    @staticmethod
    def read_offset(script, index, length):
        value = script[index : index+length]
        return int.from_bytes(value, 'little')