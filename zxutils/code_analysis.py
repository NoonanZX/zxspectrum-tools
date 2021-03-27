import sys

from .opcodes import opcodes
from . import memory
from .disasm import decode


opcodes[0x10]['flow'] = (True , 'relative') # DJNZ nn

opcodes[0x18]['flow'] = (False, 'relative') # JR nn
opcodes[0x38]['flow'] = (True , 'relative') # JR C,nn
opcodes[0x30]['flow'] = (True , 'relative') # JR NC,nn
opcodes[0x28]['flow'] = (True , 'relative') # JR Z,nn
opcodes[0x20]['flow'] = (True , 'relative') # JR NZ,nn

opcodes[0xC3]['flow'] = (False, 'absolute') # JP nn
opcodes[0xDA]['flow'] = (True , 'absolute') # JP C,nn
opcodes[0xD2]['flow'] = (True , 'absolute') # JP NC,nn
opcodes[0xCA]['flow'] = (True , 'absolute') # JP Z,nn
opcodes[0xC2]['flow'] = (True , 'absolute') # JP NZ,nn
opcodes[0xF2]['flow'] = (True , 'absolute') # JP P,nn
opcodes[0xFA]['flow'] = (True , 'absolute') # JP M,nn
opcodes[0xE2]['flow'] = (True , 'absolute') # JP PO,nn
opcodes[0xEA]['flow'] = (True , 'absolute') # JP PE,nn
opcodes[0xE9]['flow'] = (False, 'indirect') # JP (HL)

opcodes[0xCD]['flow'] = (True , 'absolute') # CALL nn
opcodes[0xDC]['flow'] = (True , 'absolute') # CALL C,nn
opcodes[0xD4]['flow'] = (True , 'absolute') # CALL NC,nn
opcodes[0xCC]['flow'] = (True , 'absolute') # CALL Z,nn
opcodes[0xC4]['flow'] = (True , 'absolute') # CALL NZ,nn
opcodes[0xF4]['flow'] = (True , 'absolute') # CALL P,nn
opcodes[0xFC]['flow'] = (True , 'absolute') # CALL M,nn
opcodes[0xE4]['flow'] = (True , 'absolute') # CALL PO,nn
opcodes[0xEC]['flow'] = (True , 'absolute') # CALL PE,nn

opcodes[0xC9]['flow'] = (False, False) # RET
opcodes[0xD8]['flow'] = (True , False) # RET C
opcodes[0xD0]['flow'] = (True , False) # RET NC
opcodes[0xC8]['flow'] = (True , False) # RET Z
opcodes[0xC0]['flow'] = (True , False) # RET NZ
opcodes[0xF0]['flow'] = (True , False) # RET P
opcodes[0xF8]['flow'] = (True , False) # RET M
opcodes[0xE0]['flow'] = (True , False) # RET PO
opcodes[0xE8]['flow'] = (True , False) # RET PE

opcodes[0xC7]['flow'] = (True , 0x00) # RST 00h
opcodes[0xCF]['flow'] = (True , 0x08) # RST 08h
opcodes[0xD7]['flow'] = (True , 0x10) # RST 10h
opcodes[0xDF]['flow'] = (True , 0x18) # RST 18h
opcodes[0xE7]['flow'] = (True , 0x20) # RST 20h
opcodes[0xEF]['flow'] = (True , 0x28) # RST 28h
opcodes[0xF7]['flow'] = (True , 0x30) # RST 30h
opcodes[0xFF]['flow'] = (True , 0x38) # RST 38h

opcodes[0xED][0x4D]['flow'] = (False, False) # RETI
opcodes[0xED][0x45]['flow'] = (False, False) # RETN
opcodes[0xED][0x55]['flow'] = (False, False) # RETN
opcodes[0xED][0x5D]['flow'] = (False, False) # RETN
opcodes[0xED][0x65]['flow'] = (False, False) # RETN
opcodes[0xED][0x6D]['flow'] = (False, False) # RETN
opcodes[0xED][0x75]['flow'] = (False, False) # RETN
opcodes[0xED][0x7D]['flow'] = (False, False) # RETN

opcodes[0xDD][0xE9]['flow'] = (False, 'indirect') # JP (IX)
opcodes[0xFD][0xE9]['flow'] = (False, 'indirect') # JP (IY)


class CodeAnalyzer:

    def __init__(self, ram):
        self.ram = ram

        self.map = [None] * 0x10000
        self._blocks = {}
        self._jumps = {}


    def add_entry_point(self, addr):
        addr = memory.wrap(addr)
        if addr < 0x4000:
            return

        connect_to_next_block = False
        new_entry_points = set()

        org = addr

        while True:
            if addr == 0x10000:
                sys.stderr.write('Warning: memory end reached.\n')
            elif self.map[addr]:
                connect_to_next_block = True
            else:
                op = decode(self.ram, addr)
                if op:
                    next_addr = addr + op['size']

                    if next_addr > 0x10000:
                        sys.stderr.write('Warning: instruction at #%04X is out of memory.\n' % addr)
                    elif any([flag is not None for flag in self.map[addr:next_addr]]):
                        sys.stderr.write('Warning: instruction at #%04X overlaps another one.\n' % addr)
                    else:
                        self.map[addr:next_addr] = [True] + [False] * (op['size'] - 1)

                        cont, jump = op['flow'] if 'flow' in op else (True, False)

                        if jump:
                            if jump is int:
                                jump_addr = jump
                            elif jump == 'absolute':
                                jump_addr = memory.get_word(self.ram, next_addr - 2)
                            elif jump == 'relative':
                                jump_addr = memory.wrap(next_addr + memory.get_sbyte(self.ram, next_addr - 1))
                            else:
                                sys.stderr.write('Warning: indirect jump at #%04X - cannot follow.\n' % addr)
                                jump_addr = None

                            self._jumps[addr] = jump_addr
                            if jump_addr is not None:
                                new_entry_points.add(jump_addr)

                        addr = next_addr

                        if cont:
                            continue
            break

        end = addr

        if org < end:
            if connect_to_next_block:
                end = self._blocks.pop(end)[1]
            self._blocks[org] = (org, end)

        for ep in new_entry_points:
            self.add_entry_point(ep)


    def get_code_blocks(self):
        return [self._blocks[addr] for addr in sorted(self._blocks)]


    def get_jumps(self):
        return self._jumps
