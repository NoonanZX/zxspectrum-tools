import sys
import os


def create():
    return [[] for i in range(0x10000)]


_pages = ['07', '05', '02', '00']


def load(filename):
    if not os.path.isfile(filename):
        sys.exit('File "%s" not found.' % filename)

    labels = create()

    for line in open(filename).readlines():
        line = line.strip()
        if line:
            try:
                addr, label = line.split()
                page, addr = [part.strip() for part in addr.split(':')]

                page = _pages.index(page) if page else 0
                addr = int(addr, 16)

                if not 0 <= addr < 0x4000:
                    raise ValueError()

                addr = page * 0x4000 + addr
                labels[addr].append(label)
            except ValueError:
                sys.stderr.write('Warning: invalid label "%s" in file "%s".\n' % (line, filename))

    return labels


def save(filename, labels):
    with open(filename, 'w') as f:
        for addr in range(0x10000):
            for label in labels[addr]:
                f.write(_pages[addr // 0x4000])
                f.write(':')
                f.write('%04X' % (addr % 0x4000))
                f.write(' ')
                f.write(label)
                f.write('\n')
