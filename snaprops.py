#!/usr/bin/env python

from __future__ import print_function
import sys
import os
import struct
import argparse


file_types = {49179: 48, 131103: 128, 147487: 128}
prop_names = ('I', "HL'", "DE'", "BC'", "AF'", 'HL', 'DE', 'BC', 'IY', 'IX', 'INT_FLAGS', 'R', 'AF', 'SP', 'INT_MODE', 'BORDER', 'PC', '7FFD', 'TRDOS_ROM')
prop_sizes = ( 1,   2,     2,     2,     2,     2,    2,    2,    2,    2,    1,           1,   2,    2,    1,          1,        2,    1,      1         )


def error(msg):
    sys.exit('Error: ' + msg)

def warning(msg):
    sys.stderr.write('Warning: ' + msg + '\n')


def get_file_type(filename):
    if not os.path.isfile(filename):
        error('File "%s" not found.' % filename)

    size = os.path.getsize(filename)
    if size not in file_types:
        error('File "%s" is not a valid SNA file.' % filename)

    return file_types[size]


def load_file_props(filename):
    type = get_file_type(filename)

    with open(filename, 'rb') as f:
        props = {}

        props['I'],\
        props["HL'"],\
        props["DE'"],\
        props["BC'"],\
        props["AF'"],\
        props['HL'],\
        props['DE'],\
        props['BC'],\
        props['IY'],\
        props['IX'],\
        props['INT_FLAGS'],\
        props['R'],\
        props['AF'],\
        props['SP'],\
        props['INT_MODE'],\
        props['BORDER'],\
        = struct.unpack('<BHHHHHHHHHBBHHBB', f.read(27))

        if type == 48:
            if 0x4000 <= props['SP'] <= 0xFFFE:
                f.seek(27 + props['SP'] - 0x4000)
                props['PC'], = struct.unpack('<H', f.read(2))
            else:
                warning('Format is 48k and SP is out of RAM, setting PC = 0.')
                props['PC'] = 0

            props['SP'] += 2
            props['SP'] %= 0x10000

            props['7FFD'] = props['TRDOS_ROM'] = None
        else:
            f.seek(49179)

            props['PC'],\
            props['7FFD'],\
            props['TRDOS_ROM'],\
            = struct.unpack('<HBB', f.read(4))

        return props


def save_file_props(filename, props):
    type = get_file_type(filename)

    with open(filename, 'r+b') as f:
        f.write(struct.pack('<BHHHHHHHHHBBHHBB',\
        props['I'],\
        props["HL'"],\
        props["DE'"],\
        props["BC'"],\
        props["AF'"],\
        props['HL'],\
        props['DE'],\
        props['BC'],\
        props['IY'],\
        props['IX'],\
        props['INT_FLAGS'],\
        props['R'],\
        props['AF'],\
        props['SP'] if type == 128 else (props['SP'] - 2) % 0x10000,\
        props['INT_MODE'],\
        props['BORDER'],\
        ))

        if type == 48:
            if props['SP'] - 2 >= 0x4000:
                f.seek(27 + props['SP'] - 2 - 0x4000)
                f.write(struct.pack('<H', props['PC']))
            else:
                warning('Format is 48k and SP is out of RAM making it impossible to save PC.')

            for name in '7FFD', 'TRDOS_ROM':
                if props[name] is not None:
                    warning('Ignoring %s in 48k format.' % name)
        else:
            f.seek(49179)

            f.write(struct.pack('<HBB',\
            props['PC'],\
            props['7FFD'],\
            props['TRDOS_ROM'],\
            ))


def patch_prop(props, name, value):
    if name not in prop_names:
        warning('Unknown property %s - skipped.' % name)
        return

    try:
        value = int(value, 0)
    except:
        warning('%s is not an integer - skipped.' % name)
        return

    size = prop_sizes[prop_names.index(name)]

    if not 0 <= value < (1 << 8 * size):
        warning('%s is out of range [0,0x%s] - skipped.' % (name, 'FF' * size))
        return

    props[name] = value


def input_props(props):
    for line in sys.stdin:
        parts = line.split()
        if len(parts) >= 2:
            patch_prop(props, parts[0], parts[1])
        else:
            warning('Invalid line "%s" - skipped.' % line.strip())


def print_props(props):
    for name, size in zip(prop_names, prop_sizes):
        prop = props[name]
        if prop is not None:
            if size > 1:
                prop = '0x%04X' % prop
            elif prop > 0:
                prop = '0x%X' % prop
            else:
                prop = '0'
            print(name, prop, sep = ' ' * (max(16 - len(name), 1)))


usage = 'snaprops.py filename [-r] [-w] [-rw] [[-{' + '|'.join(prop_names) + '}=value]]'
usage += '\n\t                Reads, writes and patches properties of SNA files.'
usage += '\n\tfilename      - name of SNA-file (both 48k and 128k formats are supported)'
usage += '\n\t-r            - reads properties from SNA-file and prints them to <stdout> (automatically set if no other options specified)'
usage += '\n\t-w            - reads properties from <stdin> and writes them into SNA-file'
usage += '\n\t-rw           - same as -r plus -w'
usage += '\n\t-<PROP>=value - patches selected property with new value, where <PROP> is one of:'
usage += '\n\t                ' + ','.join(prop_names)
usage += "\n\tHint: To copy properties from one snapshot to another use - './snaprops.py -r src-file.sna | ./snaprops.py -w dst-file.sna'."

parser = argparse.ArgumentParser(add_help = False, usage = usage)
parser.add_argument('filename')
parser.add_argument('-r', action = 'store_true')
parser.add_argument('-w', action = 'store_true')
parser.add_argument('-rw', action = 'store_true')
for name in prop_names:
    parser.add_argument('-' + name)
args = parser.parse_args()

if args.rw:
    args.r = args.w = True


props = load_file_props(args.filename)

if args.w:
    input_props(props)

for name in prop_names:
    prop = vars(args)[name]
    if prop is not None:
        patch_prop(props, name, prop)
        args.w = True

if args.w:
    save_file_props(args.filename, props)
else:
    args.r = True

if args.r:
    print_props(props)
