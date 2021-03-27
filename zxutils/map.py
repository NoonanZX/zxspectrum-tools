import sys
import os
from struct import unpack


def load(filename):
    if not os.path.isfile(filename):
        sys.exit('File "%s" not found.' % filename)

    size = os.path.getsize(filename)
    if size != 0x2000:
        sys.exit('File "%s" is not a valid MAP file.' % filename)

    data = bytearray(open(filename, 'rb').read())
    return [data[i // 8] & 1 << i % 8 != 0 for i in range(0x10000)]


def merge(maps):
    if not maps:
        return [False] * 0x10000

    map = maps[0]
    for i in range(1, len(maps)):
        for j in range(0x10000):
            if maps[i][j]:
                map[j] = True

    return map


def save(filename, map):
    with open(filename, 'wb') as f:
        data = bytearray([sum([1 << j if map[i * 8 + j] else 0 for j in range(8)]) for i in range(0x2000)])
        f.write(data)
