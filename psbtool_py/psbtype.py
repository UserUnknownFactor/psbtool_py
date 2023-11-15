from enum import IntEnum

class PSBType(IntEnum):
    NONE = 0,
    NULL = 1,
    FALSE = 2,
    TRUE = 3,

    # 0 <= N <= 8
    # NOTE: usual items (base [- 1] + N)
    INTEGER_N = 4,

    FLOAT0 = 0x1d,
    FLOAT = 0x1e,
    DOUBLE = 0x1f,

    # 1 <= N <= 8; N is count mask
    INTEGER_ARRAY_N = 0x0C,

    # 1 <= N <= 4; index of key name, only used in PSBv1
    KEY_NAME_N = 0x10,

    # 1 <= N <= 4
    STRING_N = 0x14,

    # 1 <= N <= 4
    RESOURCE_N = 0x18,

    LIST = 0x20, # object list
    OBJECT = 0x21, # object dictionary

    # 1 <= N <= 8
    EXTRA_N = 0x21,

    # NOTE: used by compiler; they're NOPs
    COMPILER_INTEGER = 0x80,
    COMPILER_STRING = 0x81,
    COMPILER_RESOURCE = 0x82,
    COMPILER_DECIMAL = 0x83,
    COMPILER_ARRAY = 0x84,
    COMPILER_BOOL = 0x85,
    COMPILER_BINARY_TREE = 0x86

PSB_SIGNATURE = b'PSB\0'
PSB_MDF_SIGNATURE = b'MDF\0'

class PackageStatus:
    MDF = 0
    PSB = 1
    Invalid = 2