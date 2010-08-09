#/usr/bin/env python3.0
#incomplete thumb disassembler

import sys
import os
from struct import pack, unpack

class OpcodeType(type):
    def __new__(cls, name, bases, dict):
        if 'pattern' in dict:
            dict['mask'], dict['maskval'] = parse_pattern(dict['pattern'])
        return super().__new__(cls, name, bases, dict)

class Opcode(metaclass=OpcodeType):
    @classmethod
    def match(cls, word):
        return (word & cls.mask) == cls.maskval
    def setstate(self, state):
        pass

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

class Jump:
    def __init__(self, addr):
        self.addr = addr
    def __str__(self):
        return ":{:08X}".format(self.addr)

class UndefinedOpcode(Opcode):
    def __init__(self, word):
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

        def __init__(self, word):
            self.word = word
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

        def __init__(self, word):
            self.word = word
            self.dest = Register(word >> 8 & 0b111)
            self.a = Immed(word & 0xff)
        
        def __str__(self):
            return "add {self.dest},{self.a}".format(self=self)

    class JumpOpcode(Opcode):
        def setstate(self, state):
            super().setstate(state)
            if state.pc is not None:
                self.jmp = Jump(state.pc + self.offset)

    @opcode
    class B_1(JumpOpcode):
        pattern = '1101 xxxx xxxxxxxx'

        conds = "eq ne lo hs mi pl vs vc hi ls ge lt gt le al nv".split()

        def __init__(self, word):
            self.word = word

            self.cond = word >> 8 & 0xf

            self.offset = signextend(word & 0xff, 8) * 2
            self.jmp = None

        def __str__(self):
            cond = '' if self.cond == 14 else self.conds[self.cond]
            return "b{} {self.jmp}".format(cond, self=self)

    @opcode
    class B_2(JumpOpcode):
        pattern = '11100 xxxxxxxxxxx'

        def __init__(self, word):
            self.word = word
            self.offset = signextend(word & 0x7ff, 11) * 2
            self.jmp = None

        def __str__(self):
            return "b {self.jmp}".format(self=self)

    @opcode
    class BL(JumpOpcode):
        def __init__(self, dword):
            self.word = dword

            n = (dword >> 16 & 0x7ff) << 12 
            n += (dword & 0x7ff) << 1
            n = signextend(n, 11+11+1)
            self.offset = n
            self.jmp = None

        @classmethod
        def match(cls, word):
            return False

        def __str__(self):
            return "bl {self.jmp}".format(self=self)

    @opcode
    class BLX(BL):
        def __init__(self, dword):
            super().__init__(dword)
            assert dword & 1 == 0

        def setstate(self, state):
            super().setstate(state)
            if self.jmp is not None:
                self.jmp.addr &= ~3

        def __str__(self):
            return "blx {self.jmp}".format(self=self)

    @opcode
    class CMP_1(Opcode):
        pattern = '00101 xxx xxxxxxxx'

        def __init__(self, word):
            self.word = word
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

        def __init__(self, word):
            self.word = word
            self.dest = Register(word & 0b111)
            self.a = Register(word >> 3 & 0b111)
        
        def __str__(self):
            return "mul {self.dest},{self.a}".format(self=self)

    @opcode
    class LDR_3(Opcode):
        pattern = '01001 xxx xxxxxxxx'

        def __init__(self, word):
            self.word = word
            self.dest = Register(word >> 8 & 0b111)
            self.offset = (word & 0xff) * 4
            self.addr = None
            self.value = None

        def setstate(self, state):
            if state.pc is not None:
                self.addr = (state.pc & ~3) + self.offset
                if state.data is not None:
                    self.value = Immed(
                        unpack("<L", state.data[self.addr:self.addr+4])[0]
                    )
            super().setstate(state)

        def __str__(self):
            if self.value is not None:
                return "ldr {self.dest},={self.value}\t; [{self.addr:#08x}]".format(self=self)
            else:
                return "ldr {self.dest},[{self.addr:#08x}]".format(self=self)
            return s

    @opcode
    class PUSH(Opcode):
        pattern = '1011 010 x xxxxxxxx'

        def __init__(self, word):
            self.word = word
            self.registers = [Register(i) for i in range(8) if word >> i & 1]
            if word >> 8 & 1:
                self.registers.append(Register(14))

        def __str__(self):
            s = ','.join(map(str, self.registers))
            return "push {" + s + "}"

    @opcode
    class POP(Opcode):
        pattern = '1011 110 x xxxxxxxx'

        def __init__(self, word):
            self.word = word
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
        self.size = os.path.getsize(f.name)
    
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
    
class State:
    pass

def dis(f, base=BASE, skip_undefined=True):
    def out(pc, word, s=None, *args, **kwargs):
        print(":{0:08X} {1:04X}     {2}".format(pc-4, word, s))
    def out2(pc, word, s=None, *args, **kwargs):
        print(":{0:08X} {1:08X} {2}".format(pc-4, word, s))

    data = ROMFile(f, base)
    state = State()
    state.pc = 0
    state.data = data

    for word in data.iterwords():
        state.pc = data.pc
        if word >> 11 == 0b11110:
            # special processing for the BL instruction
            word2 = data.readword()
            dword = word << 16 | word2
            if word2 >> 11 == 0b11111:
                op = Thumb.BL(dword)
                op.setstate(state)
                out2(state.pc, dword, op)
            elif word2 >> 11 == 0b11101:
                op = Thumb.BLX(dword)
                op.setstate(state)
                out2(state.pc, dword, op)
            else:
                #op = UndefinedOpcode(word, pc_)
                #out(pc_, word, str(op))
                #op = UndefinedOpcode(word2, data.pc)
                #out(data.pc, word, str(op))
                out2(state.pc, dword, UndefinedOpcode(dword))
        else:   
            op = parse_opcode(word)
            op.setstate(state)
            if skip_undefined and type(op) is UndefinedOpcode:
                pass
            else:
                out(data.pc, word, str(op))
    


def parse_opcode(word):
    # A dumb O(n) search
    for opcode in Thumb._opcodes:
        if opcode.match(word):
            return opcode(word)
    return UndefinedOpcode(word)

if __name__ == '__main__':
    f = open(sys.argv[1], 'rb')
    dis(f, 0x2246770, skip_undefined=False)
    

