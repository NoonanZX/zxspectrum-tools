import sys
import os
from struct import unpack


_types = {0xC01B: 48, 0x2001F: 128, 0x2401F: 128}


def load(filename):
    if not os.path.isfile(filename):
        sys.exit('File "%s" not found.' % filename)

    size = os.path.getsize(filename)
    if size not in _types:
        sys.exit('File "%s" is not a valid SNA file.' % filename)

    with open(filename, 'rb') as f:
        type = _types[size]

        f.seek(23)
        sp, = unpack('<H', f.read(2))

        f.seek(27)
        ram = bytearray(f.read(0xC000))

        if type == 48:
            if not 0x4000 <= sp <= 0xFFFC:
                sys.exit('Can\'t load file "%s" - SP is out of RAM.' % filename)

            pc = ram[sp - 0x4000] + ram[sp + 1 - 0x4000] * 256
            sp += 2
        else:
            pc, = unpack('<H', f.read(2))

        return {'type': type, 'ram': ram, 'pc': pc, 'sp': sp}
