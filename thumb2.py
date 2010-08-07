#/usr/bin/env python3.0
#incomplete thumb disassembler

import sys
from struct import pack, unpack

class OpcodeType(type):
    def __new__(cls, name, bases, dict):
        if 'pattern' in dict:
            dict['mask'], dict['maskval'] = parse_pattern(dict['pattern'])
        return super(OpcodeType, cls).__new__(cls, name, bases, dict)

class Opcode(metaclass=OpcodeType):
    @classmethod
    def match(cls, word):
        return (word & cls.mask) == cls.maskval

class Register:
    def __init__(self, n):
        self.n = n
    def __str__(self):
        if self.n == 14:
            return "sp"
        elif self.n == 15:
            return "pc"
        return "r{}".format(self.n)

class Immed:
    def __init__(self, n):
        self.n = n
    def __str__(self):
        if self.n < 10:
            return str(self.n)
        return "#{:#x}".format(self.n)
    def __bool__(self):
        return bool(self.n)

class UndefinedOpcode:
    def __init__(self, word, pc):
        self.word = word
    def __str__(self):
        return "<undefined opcode>"

def parse_pattern(pattern):
    mask = int(''.join('1' if bit in ('1', '0') else '0'
                       for bit in pattern
                       if not bit.isspace()),
               2)
    maskval = int(''.join('1' if bit == '1' else '0'
                          for bit in pattern
                          if not bit.isspace()),
                  2)
    assert len(pattern.replace(" ", '')) == 16
    return mask, maskval

class Thumb:

    _opcodes = []

    def opcode(cls, *, _opcodes=_opcodes):
        _opcodes.append(cls)
        return cls

    @opcode
    class ADD_1(Opcode):
        pattern = '000 11 10 xxx xxx xxx'

        def __init__(self, word, pc):
            self.word = word
            self.pc = pc
            self.dest = Register(word & 0b111)
            self.a = Register(word >> 3 & 0b111)
            self.b = Immed(word >> 6 & 0b111)
        
        def __str__(self):
            if self.b:
                return "add {self.dest},{self.a},{self.b}".format(self=self)
            else:
                return "mov {self.dest},{self.a}".format(self=self)

    @opcode
    class ADD_2(Opcode):
        pattern = '001 10 xxx xxxxxxxx'

        def __init__(self, word, pc):
            self.word = word
            self.pc = pc
            self.dest = Register(word >> 8 & 0b111)
            self.a = Immed(word & 0xff)
        
        def __str__(self):
            return "add {self.dest},{self.a}".format(self=self)

    @opcode
    class B_1(Opcode):
        pattern = '1101 xxxx xxxxxxxx'

        conds = "eq ne lo hs mi pl vs vc hi ls ge lt gt le al nv".split()

        def __init__(self, word, pc):
            self.word = word
            self.pc = pc

            self.cond = word >> 8 & 0xf

            n = signextend(word & 0xff, 8)
            self.jmp = self.pc + (n * 2)
        
        def __str__(self):
            cond = '' if self.cond == 14 else self.conds[self.cond]
            return "b{} #{self.jmp:#08x}".format(cond, self=self)

    @opcode
    class B_2(Opcode):
        pattern = '11100 xxxxxxxxxxx'

        def __init__(self, word, pc):
            self.word = word
            self.pc = pc

            n = signextend(word & 0x7ff, 11)
            self.jmp = self.pc + (n * 2)
        
        def __str__(self):
            return "b #{self.jmp:#08x}".format(self=self)

    @opcode
    class BL(Opcode):
        def __init__(self, dword, pc):
            self.word = dword
            self.pc = pc

            n = (dword >> 16 & 0x7ff) << 12 
            n += (dword & 0x7ff) << 1
            n = signextend(n, 11+11+1)
            self.jmp = pc + n
        
        @classmethod
        def match(cls, word):
            return False

        def __str__(self):
            return "bl #{self.jmp:#08x}".format(self=self)

    @opcode
    class BLX(BL):
        def __str__(self):
            return "blx #{self.jmp:#08x}".format(self=self)

    @opcode
    class CMP_1(Opcode):
        pattern = '00101 xxx xxxxxxxx'

        def __init__(self, word, pc):
            self.word = word
            self.pc = pc
            self.a = Register(word >> 8 & 0b111)
            self.b = Immed(word & 0xff)

        def __str__(self):
            return "cmp {self.a},{self.b}".format(self=self)

    @opcode
    class CMP_2(CMP_1):
        pattern = '010000 0101 xxx xxx'

        def __init__(self, word, pc):
            self.word = word
            self.pc = pc
            self.a = Register(word & 0x111)
            self.b = Register(word >> 3 & 0x111)

    @opcode
    class MOV_1(ADD_2):
        pattern = '00100 xxx xxxxxxxx'

        def __str__(self):
            return "mov {self.dest},{self.a}".format(self=self)

    @opcode
    class MUL(Opcode):
        pattern = '010000 1101 xxx xxx'
        mask, maskval = parse_pattern(pattern)

        def __init__(self, word, pc):
            self.word = word
            self.pc = pc
            self.dest = Register(word & 0b111)
            self.a = Register(word >> 3 & 0b111)
        
        def __str__(self):
            return "mul {self.dest},{self.a}".format(self=self)

    @opcode
    class PUSH(Opcode):
        pattern = '1011 010 x xxxxxxxx'

        def __init__(self, word, pc):
            self.word = word
            self.pc = pc
            self.registers = [Register(i) for i in range(8) if word >> i & 1]
            if word >> 8 & 1:
                self.registers.append(Register(14))

        def __str__(self):
            s = ','.join(map(str, self.registers))
            return "push {" + s + "}"

    @opcode
    class POP(Opcode):
        pattern = '1011 110 x xxxxxxxx'

        def __init__(self, word, pc):
            self.word = word
            self.pc = pc
            self.registers = [Register(i) for i in range(8) if word >> i & 1]
            if word >> 8 & 1:
                self.registers.append(Register(15))

        def __str__(self):
            s = ','.join(map(str, self.registers))
            return "pop {" + s + "}"

BASE = 0x02000000

def signextend(n, size=16):
    sign = n >> (size - 1)
    if sign == 0:
        return n
    else:
        return n - (1 << (size))

class ROMFile:
    def __init__(self, f, base):
        self.f = f
        self.base = base
    
    @property
    def pc(self):
        return f.tell() + self.base + 2
    
    def readat(self, base):
        pass
        

    def read(self, count):
        if self.pos + count < self.base:
            toread = count + self.base - self.pos
            return b'\x00' * (toread - count) + self.readat(self.base, count)
        elif 0:
            self.pos

    def __getitem__(self, key):
        if isinstance(key, slice):
            start = key.start - self.base
            stop = key.stop - self.base

            prefixcount = 0
            if start < 0:
                prefixcount = min(0, stop) - start
                start = 0

            postfixcount = 0
            if self.size < stop:
                postfixcount = stop - max(self.size, start)
                stop = self.size

            count = stop - start

            here = self.f.tell()
            try:
                self.f.seek(start)
                data = self.f.read(count)
            finally:
                self.f.seek(here)

            return (b'\x00' * prefixcount +
                    data + 
                    b'\x00' * postfixcount)

    def readbyte(self):
        return self.read(1)[0]

    def readword(self):
        return unpack("<H", f.read(2))[0]

    def readlong(self):
        return unpack("<L", f.read(4))[0]

    def seek(self, pos, mode):
        self.f.seek(pos, mode)

    def iterwords(self):
        while True:
            x = f.read(2)
            if len(x) < 2:
                break
            yield unpack("<H", x)[0]

    def copy(self):
        from copy import copy
        return ROMFile(copy(self.f), self.base)
    

def dis(f, base=BASE, skip_undefined=True):
    def out(pc, word, s=None, *args, **kwargs):
        print("{0:08X} {1:04X}     {2}".format(pc-4, word, s))
    def out2(pc, word, s=None, *args, **kwargs):
        print("{0:08X} {1:08X} {2}".format(pc-4, word, s))

    data = ROMFile(f, base)

    for word in data.iterwords():
        # special processing for the BL instruction
        if word >> 11 == 0b11110:
            pc_ = data.pc
            word2 = data.readword()
            dword = word << 16 | word2
            if word2 >> 11 == 0b11111:
                op = Thumb.BL(dword, pc_)
                out2(pc_, dword, op)
            elif word2 >> 11 == 0b11101:
                op = Thumb.BLX(dword, pc_)
                out2(pc_, dword, op)
            else:
                #op = UndefinedOpcode(word, pc_)
                #out(pc_, word, str(op))
                #op = UndefinedOpcode(word2, data.pc)
                #out(data.pc, word, str(op))
                out2(pc_, dword, UndefinedOpcode(dword, pc_))
        else:   
            op = parse_opcode(word, data)
            if skip_undefined and type(op) is UndefinedOpcode:
                pass
            else:
                out(data.pc, word, str(op))
    

"""
        if bits.startswith('111'):
            h = word >> 11 & 0b10
            if h == 0b00:
                jmp = pc + (word & 0x7ff)
                out(pc, word, "b 0x{0:08x}", jmp,)
            elif h == 0b10:
                jmp = pc + (signextend(word & 0x7ff, 11) << 12)
                nword = next(g)
                pc += 2
                if nword >> 13 == 0b111:
                    h2 = nword >> 11 & 0b11
                    if h2 == 0b11:
                        jmp += ((nword & 0x7ff) << 1)
                        out(pc-2, word, "bl 0x{0:08x}", jmp)
                        #out(pc, nword, "*blh")
                    elif h2 == 0b01:
                        jmp = (jmp + ((nword & 0x7ff) << 1)) & 0xfffffffc
                        out(pc-2, word, "blx 0x{0:08x}", jmp)
                else:
                    out(pc-2, word, "<bl missing blh>", word)
                    word = nword
                    continue
        else:
            #out(pc, "{0:04x}".format(word))
            #break
            pass
"""

def parse_opcode(word, data):
    # A dumb O(n) search
    for opcode in Thumb._opcodes:
        if opcode.match(word):
            return opcode(word, data.pc)
    return UndefinedOpcode(word, data.pc)

if __name__ == '__main__':
    f = open(sys.argv[1], 'rb')
    dis(f, 0x2246770)
    

