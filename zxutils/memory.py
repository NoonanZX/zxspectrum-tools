import sys


def wrap(addr):
    if addr >= 0x10000:
        sys.stderr.write('Warning: memory address is #%X - wrapped to #%04X.\n' % (addr, addr % 0x10000))
        addr %= 0x10000
    return addr


def get_byte(ram, addr):
    addr = wrap(addr)
    if addr < 0x4000:
        sys.stderr.write('Warning: accessing rom memory at #%04X - returning 0.\n' % (addr, new_addr))
        return 0
    return ram[addr - 0x4000]


def get_sbyte(ram, addr):
    byte = get_byte(ram, addr)
    return byte if byte < 128 else byte - 256


def get_word(ram, addr):
    return get_byte(ram, addr) + 256 * get_byte(ram, addr + 1)
