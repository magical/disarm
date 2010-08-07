#/usr/bin/env python3.0
#incomplete thumb disassembler

import sys

class Value:
    def parse(self, word):
        mask = int('1' * self.length, 2)
        self.value = (word >> (self.start-self.length)) & mask

class Constant(Value):
    def __init__(self, bits):
        self.bits = bits
        self.length = len(bits)

class Register(Value):
    length = 3

    def __str__(self):
        return 'r' + unicode(self.value)

class Immed(Value):
    def __init__(self, length):
        self.length = length

    def __str__(self):
        return "#%#x" % self.value

class SignedImmed(Immed):
    def parse(self, word):
        super(self, SignedImmed).parse(word)
        self.value = signextend(self.value, self.length)

class BaseOpcodeType:
    def __new__(klass, bases, dict):
        return type.__new__(klass, bases, dict)

    def __init__(self, name, definition):
        self.name = name
        self.definition = []

        i = 0
        for component in definition:
            component.start = i
            i += component.length

    def __str__(self):
        self.type(self.name, self.definition)

class BaseOpcode(meta=BaseOpcodeType):
    def __init__(name, word):
        for component in self.definition:
            
        

class ADD_1():
    definition = [Constant('111'), Register(), Register(), Immed(8)]

    def __init__(word):
        a, dest, b = 
        
    def __str__(self):
        

def guess_type(definition):
    types = tuple(type(component) for component in definition
                  if not isinstance(component, Constant))

    try:
        return _opcode_type_registry[types]
    except LookupError:
        raise ValueError("No opcode type for " + repr(types))

_opcode_registry = {}
def opcode(name, type, *definition):
    opcode = type(name, *definition)
    if not type:
        type = guess_type(definition)
    constants = 
    return opcode

class Opcode(OpcodeType):
    def __init__(

class Thumb:
    conds = "eq ne hs lo mi pl vs vc hi ls ge lt gt le al nv".split()

    opcode("add", Constant('111'), Register(), Register(), Immed(8))
    opcode("add", Constant(''), Register(), Register(), Register())
    @opcode(Constant(''))
    class ADD_1:

    opcode("add", DataProcessing('0101'))
    opcode("add", SpecialForm('1010'))


BASE = 0x02000000

def signextend(n, size=16):
    sign = n >> (size - 1)
    if sign == 0:
        return n
    else:
        return n - (1 << (size))

def out(pc, word, s=None, *args, **kwargs):
    #if not 0x205e400 < pc < 0x205e7ff:
    #    return
    if s is not None:
        s = s.format(*args, **kwargs)
    else:
        s = ""
    print("{0:08x} {1:04x} {2}".format(pc-4, word, s))


class ROMFile:
    def __init__(self, f, base):
        self.f = f
        self.base = base
    
    @property
    def pc(self):
        return f.tell() + self.base + 4
    
    def readat(self.base):
        

    def read(self, count):
        if self.pos + count < self.base:
            toread = count + self.base - self.pos
            return b'\x00' * (toread - count) + self.readat(self.base, count)
        elif:
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
        return unpack(">H", f.read(2))[0]

    def readlong(self):
        return unpack(">L", f.read(4))[0]

    def seek(self, pos, mode):
        self.f.seek(pos, mode)

    def iterwords(self):
        while True:
            x = f.read(2)
            if len(x) < 2:
                break
            yield unpack(">H", x)

    def copy(self):
        from copy import copy
        return ROMFile(copy(self.f), self.base)
    

def dis(f, base=BASE):
    data = ROMFile(f)

    for word in data:
        bits = format(word, "016b")
        if bits.startswith('1101'):
            jmp = pc + (signextend(word & 0xff) << 1)
            type = (word >> 8) & 0xf
            out(pc, word, "b{1} 0x{0:08x}", jmp, conds[type])
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
    bits = format(word, "016b")
    while len(bits) > 3:
        if bits in _opcode_registry:
            opcode_class = _opcode_registry[bits]
            return opcode_class(
    return UndefinedOpcode()
        

    


if __name__ == '__main__':
    f = open(sys.argv[1], 'rb')
    dis(f)
    
