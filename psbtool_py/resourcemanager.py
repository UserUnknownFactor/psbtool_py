import zlib
from .stringmanager import PSBStrMan

class PSBResManager:
    def __init__(self):
        self.packget = None
        self.EntryCount = 0
        self.ResSizePos = 0
        self.Initialized = False
        self.OffsetPos = 0
        self.OffsetSize = 0
        self.OffsetTablePos = 0
        self.StartPos = 0
        self.ResSizeOffSize = 0
        self.ResSizeOffTablePos = 0
        self.CompressPackget = False
        self.CompressionLevel = 9
        self.FixOffsets = True

    def Import(self, script):
        Status = PSBStrMan.GetPackgetStatus(script)
        if Status == PSBStrMan.PackgetStatus.MDF:
            script = PSBStrMan.ExtractMDF(script)
        Status = PSBStrMan.GetPackgetStatus(script)
        if Status != PSBStrMan.PackgetStatus.PSB:
            raise Exception("Bad File Format")

        self.packget = script
        self.StartPos = PSBStrMan.ReadOffset(self.packget, 0x20, 4)
        self.OffsetPos = PSBStrMan.ReadOffset(self.packget, 0x18, 4)
        tmp = self.GetOffsetInfo(self.packget, self.OffsetPos)
        self.OffsetSize = tmp[0]
        self.OffsetTablePos = tmp[1]
        self.ResSizePos = PSBStrMan.ReadOffset(self.packget, 0x1C, 4)
        tmp = self.GetOffsetInfo(self.packget, self.ResSizePos)
        self.ResSizeOffSize = tmp[0]
        self.ResSizeOffTablePos = tmp[1]
        Offsets = self.GetValues(self.packget, self.OffsetPos)
        Sizes = self.GetValues(self.packget, self.ResSizePos)
        self.EntryCount = len(Offsets)
        Files = []
        for i in range(self.EntryCount):
            EndPos = Offsets[i] + Sizes[i]
            data = self.packget[EndPos + self.StartPos]
            Files.append(FileEntry(data))
        self.Initialized = True
        return Files

    def GetOffsetInfo(self, file, pos):
        OffSize = PSBStrMan.ConvertSize(file[pos])
        Count = PSBStrMan.ReadOffset(file, pos + 1, OffSize)
        pos += 1 + OffSize
        return [PSBStrMan.ConvertSize(file[pos]), pos + 1, Count]

    def GetValues(self, file, pos):
        tmp = self.GetOffsetInfo(file, pos)
        Result = []
        pos = tmp[1]
        OffSize = tmp[0]
        for i in range(tmp[2]):
            Result.append(PSBStrMan.ReadOffset(file, pos + (i * OffSize), OffSize))
        return Result

    def Export(self, Resources):
        if not self.Initialized:
            raise Exception("You need to import before you can export!")
        if len(Resources) != self.EntryCount:
            raise Exception("You can't add or delete resources!")
        TotalSize = 0
        for i in range(len(Resources)):
            TotalSize += len(Resources[i].Data) + (4 - ((self.StartPos + TotalSize + len(Resources[i].Data)) % 4)) if self.FixOffsets and i + 1 != len(Resources) else 0
        ResTable = bytearray(TotalSize)
        TotalSize = 0
        MainData = self.CutAt(self.packget, self.StartPos)
        for i in range(len(Resources)):
            file = Resources[i].Data
            ResTable[TotalSize:TotalSize + len(file)] = file
            MainData[self.OffsetTablePos + (i * self.OffsetSize):self.OffsetTablePos + (i * self.OffsetSize) + self.OffsetSize] = PSBStrMan.CreateOffset(self.OffsetSize, TotalSize)
            MainData[self.ResSizeOffTablePos + (i * self.ResSizeOffSize):self.ResSizeOffTablePos + (i * self.ResSizeOffSize) + self.ResSizeOffSize] = PSBStrMan.CreateOffset(self.ResSizeOffSize, len(file))
            TotalSize += len(file) + (4 - ((self.StartPos + TotalSize + len(file)) % 4)) if self.FixOffsets and i + 1 != len(Resources) else 0
        ResultPackget = bytearray(len(MainData) + len(ResTable))
        ResultPackget[:len(MainData)] = MainData
        ResultPackget[len(MainData):] = ResTable
        return zlib.compress(ResultPackget, self.CompressionLevel) if self.CompressPackget else ResultPackget

    def CutAt(self, Original, Pos):
        return Original[:Pos]

class FileEntry:
    def __init__(self, data):
        self.Data = data

class HuffmanTool:
    @staticmethod
    def DecompressBitmap(data):
        stream = bytearray()
        i = 0
        while i < len(data):
            cmd = data[i]
            if HuffmanTool.Repeat(cmd):
                Times = HuffmanTool.GetInt(cmd) + 3
                Data = data[i + 1:i + 5]
                i += 5
                for count in range(Times):
                    stream.extend(Data)
            else:
                Length = (HuffmanTool.GetInt(cmd) + 1) * 4
                Data = data[i + 1:i + 1 + Length]
                i += Length + 1
                stream.extend(Data)
        return stream

    @staticmethod
    def CompressBitmap(data, JumpHeader):
        if data[:2] == b'BM' and JumpHeader:
            data = data[0x36:]
        if len(data) % 4 > 0:
            data += bytearray(len(data) % 4)
        stream = bytearray()
        MaxInt = 0x7F
        MinVal = 3
        pos = 0
        while pos < len(data):
            if HuffmanTool.HaveLoop(data, pos):
                Loops = HuffmanTool.CountLoops(data, pos)
                DW = data[pos:pos + 4]
                while Loops > 0:
                    length = min(Loops - MinVal, MaxInt)
                    Loops -= length + MinVal
                    stream.append(HuffmanTool.CreateInt(length))
                    stream.extend(DW)
                    pos += (length + MinVal) * 4
            else:
                length = 0
                while not HuffmanTool.HaveLoop(data, pos + (length * 4)):
                    length += 1
                    if pos + (length * 4) >= len(data):
                        break
                while length > 0:
                    off = min(length, MaxInt)
                    stream.append(off - 1)
                    stream.extend(data[pos:pos + off * 4])
                    length -= off
                    pos += off * 4
        return stream

    @staticmethod
    def CountLoops(data, pos):
        Find = data[pos:pos + 4]
        Loops = 0
        while True:
            if data[(Loops * 4) + pos:(Loops * 4) + pos + 4] == Find:
                Loops += 1
            else:
                break
        return Loops

    @staticmethod
    def HaveLoop(data, pos):
        Find = data[pos:pos + 4]
        return HuffmanTool.CountLoops(data, pos) > 2

    @staticmethod
    def CreateInt(value):
        if value > 0x7F:
            raise Exception("Max allowed value is: 0x7F")
        return value | 0x80

    @staticmethod
    def Repeat(value):
        mask = 0x80
        return (value & mask) > 0

    @staticmethod
    def GetInt(value):
        mask = 0x7F
        return value & mask