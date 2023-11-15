import struct
import io

class StructReader:
    def __init__(self, stream, big_endian=False, encoding=None):
        self.stream = stream
        self.big_endian = big_endian
        self.encoding = encoding if encoding else 'utf-8'

    def read_struct(self, struct_type):
        instance = struct_type()
        self.read_fields(struct_type, instance)
        return instance

    def read_fields(self, struct_type, instance):
        fields = struct_type.__annotations__.items()
        for field_name, field_type in fields:
            value = self.read_field(field_type)
            setattr(instance, field_name, value)

    def read_field(self, field_type):
        if field_type == str:
            return self.read_string()
        elif field_type == int:
            return self.read_int()
        elif field_type == float:
            return self.read_float()
        elif field_type == bool:
            return self.read_bool()
        elif field_type == bytes:
            return self.read_bytes()
        elif isinstance(field_type, type) and issubclass(field_type, Struct):
            return self.read_struct(field_type)
        else:
            raise ValueError(f"Unsupported field type: {field_type}")

    def read_string(self):
        length = self.read_int()
        data = self.stream.read(length)
        return data.decode(self.encoding)

    def read_int(self):
        size = struct.calcsize('i')
        data = self.stream.read(size)
        value = struct.unpack('i', data)[0]
        return value

    def read_float(self):
        size = struct.calcsize('f')
        data = self.stream.read(size)
        value = struct.unpack('f', data)[0]
        return value

    def read_bool(self):
        size = struct.calcsize('?')
        data = self.stream.read(size)
        value = struct.unpack('?', data)[0]
        return value

    def read_bytes(self):
        length = self.read_int()
        data = self.stream.read(length)
        return data

class StructWriter:
    def __init__(self, stream, big_endian=False, encoding=None):
        self.stream = stream
        self.big_endian = big_endian
        self.encoding = encoding if encoding else 'utf-8'

    def write_struct(self, struct_instance):
        self.write_fields(struct_instance)

    def write_fields(self, struct_instance):
        fields = struct_instance.__annotations__.items()
        for field_name, field_type in fields:
            value = getattr(struct_instance, field_name)
            self.write_field(value, field_type)

    def write_field(self, value, field_type):
        if field_type == str:
            self.write_string(value)
        elif field_type == int:
            self.write_int(value)
        elif field_type == float:
            self.write_float(value)
        elif field_type == bool:
            self.write_bool(value)
        elif field_type == bytes:
            self.write_bytes(value)
        elif isinstance(field_type, type) and issubclass(field_type, Struct):
            self.write_struct(value)
        else:
            raise ValueError(f"Unsupported field type: {field_type}")

    def write_string(self, value):
        encoded_value = value.encode(self.encoding)
        length = len(encoded_value)
        self.write_int(length)
        self.stream.write(encoded_value)

    def write_int(self, value):
        data = struct.pack('i', value)
        self.stream.write(data)

    def write_float(self, value):
        data = struct.pack('f', value)
        self.stream.write(data)

    def write_bool(self, value):
        data = struct.pack('?', value)
        self.stream.write(data)

    def write_bytes(self, value):
        length = len(value)
        self.write_int(length)
        self.stream.write(value)

class Struct:
    pass

class AdvancedBinary(Struct):
    class StringStyle(Struct):
        CString = 0
        UCString = 1
        PString = 2

    class CString(Struct):
        pass

    class UCString(Struct):
        pass

    class PString(Struct):
        def __init__(self, prefix_type, unicode_length=False):
            self.prefix_type = prefix_type
            self.unicode_length = unicode_length

    class FString(Struct):
        def __init__(self, length):
            self.length = length

    class FArray(Struct):
        def __init__(self, length):
            self.length = length

    class PArray(Struct):
        def __init__(self, prefix_type):
            self.prefix_type = prefix_type

    class StructField(Struct):
        pass

class Tools:
    @staticmethod
    def get_struct_length(struct_instance):
        length = 0
        fields = struct_instance.__annotations__.items()
        for field_name, field_type in fields:
            if field_type == str:
                raise ValueError("You can't calculate struct length with strings")
            elif field_type == int:
                length += struct.calcsize('i')
            elif field_type == float:
                length += struct.calcsize('f')
            elif field_type == bool:
                length += struct.calcsize('?')
            elif field_type == bytes:
                length += struct.calcsize('i') + len(getattr(struct_instance, field_name))
            elif isinstance(field_type, type) and issubclass(field_type, Struct):
                length += Tools.get_struct_length(getattr(struct_instance, field_name))
            else:
                raise ValueError(f"Unsupported field type: {field_type}")
        return length

    @staticmethod
    def reverse(data):
        if isinstance(data, int):
            return struct.unpack('>i', struct.pack('<i', data))[0]
        elif isinstance(data, float):
            return struct.unpack('>f', struct.pack('<f', data))[0]
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

class AdvancedBinaryTools:
    @staticmethod
    def copy_stream(input_stream, output_stream):
        buffer = input_stream.read(1024 * 1024)
        while buffer:
            output_stream.write(buffer)
            buffer = input_stream.read(1024 * 1024)

    @staticmethod
    def copy_struct(input_struct, output_struct):
        fields = input_struct.__annotations__.items()
        for field_name, field_type in fields:
            value = getattr(input_struct, field_name)
            setattr(output_struct, field_name, value)

    @staticmethod
    def build_struct(struct_instance):
        stream = io.BytesIO()
        writer = StructWriter(stream)
        writer.write_struct(struct_instance)
        return stream.getvalue()

    @staticmethod
    def read_struct(data, struct_type):
        stream = io.BytesIO(data)
        reader = StructReader(stream)
        return reader.read_struct(struct_type)

# Example usage
if __name__ == '__main__':
    class MyStruct(Struct):
        name: str
        age: int
        height: float
        is_student: bool
        data: bytes

    struct_instance = MyStruct()
    struct_instance.name = "John"
    struct_instance.age = 25
    struct_instance.height = 1.75
    struct_instance.is_student = True
    struct_instance.data = b"Hello, World!"

    # Write struct to binary data
    binary_data = AdvancedBinaryTools.build_struct(struct_instance)

    # Read struct from binary data
    read_struct_instance = AdvancedBinaryTools.read_struct(binary_data, MyStruct)

    # Verify that the read struct is the same as the original struct
    assert struct_instance.name == read_struct_instance.name
    assert struct_instance.age == read_struct_instance.age
    assert struct_instance.height == read_struct_instance.height
    assert struct_instance.is_student == read_struct_instance.is_student
    assert struct_instance.data == read_struct_instance.data