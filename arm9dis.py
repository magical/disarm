#/usr/bin/env python3.0
#incomplete thumb disassembler

import sys

conds = "eq ne hs lo mi pl vs vc hi ls ge lt gt le al nv".split()

BASE = 0x02000000

f = open(sys.argv[1], 'rb')

def genwords(f):
    while True:
        b = f.read(2)
        if len(b) < 2:
            yield -1
            break
        w = b[0] | (b[1] << 8)
        yield w

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

g = genwords(f)
pc = BASE + 2

word = next(g)
pc += 2
while -1 < word:
    if word >> 12 == 0b1101:
        jmp = pc + (signextend(word & 0xff) << 1)
        type = (word >> 8) & 0xf
        out(pc, word, "b{1} 0x{0:08x}", jmp, conds[type])
    if word >> 13 == 0b111:
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

    word = next(g)
    pc += 2

