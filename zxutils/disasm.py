from __future__ import print_function
import sys

from .opcodes import opcodes
from . import memory


def _decode(ram, addr, table):
    op = table[memory.get_byte(ram, addr)]
    return op if type(op) is not list else _decode(ram, addr + 1 + op[256], op)


def decode(ram, addr):
    op = _decode(ram, addr, opcodes)

    if not op:
        sys.stderr.write('Warning: invalid instruction at #%04X.\n' % addr)

    return op


class Disassembler:

    def __init__(self, ram, labels = None, tab_size = 20, print_code_addr = False, print_data_addr = False):
        self.ram = ram
        self.labels = labels

        self.tab = ' ' * tab_size
        self.print_code_addr = print_code_addr
        self.print_data_addr = print_data_addr


    def print_label(self, label, value = None):
        if value is not None:
            label += ' ' * max(len(self.tab) - len(label), 1) + 'EQU ' + value

        print(label)


    def dump(self, org = None, end = None, size = None, align = 16):
        org, end = _get_limits(org, end, size)

        addr = org
        n = 0
        while addr < end:
            if self.labels and self.labels[addr]:
                if n > 0:
                    print()
                    n = 0
                for label in self.labels[addr]:
                    self.print_label(label)

            if n == 0:
                print(self._get_line_prefix(addr if self.print_data_addr else None), end = '')
                print('DB ', end = '')
            else:
                print(',', end = '')
            print('#%02X' % memory.get_byte(self.ram, addr), end = '')

            addr += 1
            n += 1

            if addr % align == 0:
                print()
                n = 0
        if n > 0:
            print()


    def disasm(self, org = None, end = None, size = None):
        org, end = _get_limits(org, end, size)

        addr = org
        while addr < end:
            op = decode(self.ram, addr)

            if addr + op['size'] > 0x10000:
                sys.stderr.write('Warning: instruction at [#%04X - #%04X] is falled out of memory.\n' % (addr, addr + op['size'] - 1))
                op = None
        
            if op:
                next_addr = addr + op['size']

                if self.labels:
                    for label in self.labels[addr]:
                        self.print_label(label)

                asm = op['asm']

                if 'args' in op:
                    for arg in op['args']:
                        arg_pos = addr + arg['pos']
                        arg_size = arg['size']

                        relative = 'relative' in arg and arg['relative']
                        signed = 'signed' in arg and arg['signed']

                        if arg_size == 2:
                            arg = memory.get_word(self.ram, arg_pos)
                        elif relative:
                            arg = memory.wrap(next_addr + memory.get_sbyte(self.ram, arg_pos))
                            arg_size = 2
                        elif signed:
                            arg = memory.get_sbyte(self.ram, arg_pos)
                        else:
                            arg = memory.get_byte(self.ram, arg_pos)

                        if arg_size == 2 and self.labels and self.labels[arg]:
                            arg = self.labels[arg][0]
                        elif signed:
                            arg = ('+' if arg >= 0 else '-') + '#%02X' % abs(arg)
                        else:
                            arg = '#%%0%dX' % (2 * arg_size) % arg

                        asm = asm.replace('%', arg, 1)

                print(self._get_line_prefix(addr if self.print_code_addr else None), end = '')
                print(asm)

                if self.labels:
                    for inner_addr in range(addr + 1, next_addr):
                        for label in self.labels[inner_addr]:
                            self.print_label(label, '$-%d' % (next_addr - inner_addr))

                addr = next_addr
            else:
                print()
                return self.dump(addr, end)


    def _get_line_prefix(self, addr):
        if addr is not None:
            return '._%04X' % addr + ' ' * max(len(self.tab) - 6, 1)
        else:
            return self.tab


def _get_limits(org = None, end = None, size = None):
    if org is None:
        org = 0x4000

    if end is None:
        if size is not None:
            end = min(org + size, 0x10000)
        else:
            end = 0x10000

    return org, end
