#!/usr/bin/env python

from __future__ import print_function
import sys
import os
import argparse
import zxutils


def _try_int(s, limits = None):
    try:
        i = int(s, 0)
    except:
        sys.exit('Argument "%s" is not an integer value.' % s)

    if not limits or limits[0] <= i < limits[1]:
        return i
    else:
        sys.exit('Argument "%s" is out of range.' % s)


# Parsing arguments.
usage = 'sna2asm.py filename [-s [entrypoint_1...]] [-m mapfile_1...] [-l labelsfile] [-a [none|code|data|all]] [-om outmapfile] [-ol outlabelsfile]'
usage += "\n\t           Disassembles snapshot <filename> and prints generated assembler program to <stdout>."
usage += "\n\tfilename - shapshot in SNA format (both 48k and 128k formats are supported)"
usage += "\n\t-s       - entry point(s) to start disassembly from (each could be a number in [0x4000, 0xFFFF] or PC)"
usage += "\n\t           if option is omitted - PC value from shapshot is used"
usage += "\n\t           if option specified without a value - only map file(s) used"
usage += "\n\t           if option specified without a value and no map files specified - performing raw memory dump with no code analysis"
usage += "\n\t-m       - execution map files list used to provide additional entry points to disassembly (see README.md for details)"
usage += "\n\t-l       - labels in UnrealSpeccy format (see README.md for details)"
usage += "\n\t-a       - generate address prefixes for code and/or data lines, can be 'none', 'code', 'data' or 'all'"
usage += "\n\t           if option is omitted - 'code' value is used"
usage += "\n\t           if option specified without a value - 'all' value is used"
usage += "\n\t-om      - save resulting exection map into file"
usage += "\n\t-ol      - save generated labels into file"
usage += "\n\t           See README.md for more information and examples."

parser = argparse.ArgumentParser(add_help = False, usage = usage)
parser.add_argument('filename')
parser.add_argument('-s', nargs = '*', default = ['PC'])
parser.add_argument('-m', nargs = '+')
parser.add_argument('-l')
parser.add_argument('-a', nargs = '?', choices = ['none', 'code', 'data', 'all'], default = 'data')
parser.add_argument('-om')
parser.add_argument('-ol')
args = parser.parse_args()


# Loading.
sna          = zxutils.sna.load(args.filename)
entry_points = [sna['pc'] if arg.upper() == 'PC' else _try_int(arg, (0, 0x10000)) for arg in args.s]
map          = zxutils.map.merge([zxutils.map.load(m) for m in args.m]) if args.m else None
labels       = zxutils.labels.load(args.l) if args.l else zxutils.labels.create()
print_addr   = args.a or 'all'


# Analyzing code.
analyzer = zxutils.CodeAnalyzer(sna['ram'])

for ep in entry_points:
    analyzer.add_entry_point(ep)

if map:
    for addr in range(0x10000):
        if map[addr] and not analyzer.map[addr]:
            analyzer.add_entry_point(addr)

blocks = analyzer.get_code_blocks()
jumps = analyzer.get_jumps()

jumps_reverted = [[] for i in range(0x10000)]
for jump_from in jumps:
    jump_to = jumps[jump_from]
    if jump_to is not None:
        jumps_reverted[jump_to].append(jump_from)


# Generating labels.
for addr in range(0x10000):
    labels[addr] = [label for label in labels[addr] if label.find('%04X' % addr) == -1]

for org, end in blocks:
    if labels[org]:
        proc_name = labels[org][0]
    else:
        proc_name = 'proc%04X' % org
        labels[org].append(proc_name)

    for addr in range(org + 1, end):
        if not labels[addr]:
            if jumps_reverted[addr]:
                if analyzer.map[addr]:
                    if all([org <= caller < end for caller in jumps_reverted[addr]]):
                        prefix = 'local'
                    else:
                        prefix = 'entry'
                else:
                    prefix = 'broken'
                labels[addr].append(proc_name + '.' + prefix + '%04X' % addr)

for i in range(len(blocks) + 1):
    org = blocks[i - 1][1] if i > 0 else 0x4000
    end = blocks[i][0] if i < len(blocks) else 0x10000
    if org < end and not labels[org]:
        labels[org].append('data%04X_size_%d_bytes' % (org, end - org))


# Disassembling & printing.
disassembler = zxutils.Disassembler(sna['ram'], labels, print_code_addr = print_addr in ['all', 'code'], print_data_addr = print_addr in ['all', 'data'])

print(disassembler.tab + 'DEVICE ZXSPECTRUM%d, #%04X' % (sna['type'], min(sna['sp'] + 3, 0xFFFF)))

if entry_points:
    print()
    for ep in entry_points:
        label = 'entry_point_%04X' % ep
        value = labels[ep][0] if labels[ep] else '#%04X' % ep
        disassembler.print_label(label, value)

print('\n' + disassembler.tab + 'ORG #4000')

small_labels = labels[:0x100]
labels[:0x100] = [[] for i in range(0x100)]

addr = 0x4000
for org, end in blocks:
    if addr < org:
        print(); disassembler.dump(addr, org)
    print(); disassembler.disasm(org, end)
    addr = end
if addr < 0x10000:
    print(); disassembler.dump(addr, 0x10000)

labels[:0x100] = small_labels

if any(labels[0:0x4000]):
    print()
    for addr in range(0x4000):
        for label in labels[addr]:
            disassembler.print_label(label, '#%04X' % addr) 

print()
if entry_points:
    print(disassembler.tab + 'SAVESNA "%s", entry_point_%04X' % (os.path.basename(args.filename), entry_points[0]))
print(disassembler.tab + 'LABELSLIST "user.l"')


# Saving.
if args.om:
    map = [flag == True for flag in analyzer.map]
    zxutils.map.save(args.om, map)

if args.ol:
    zxutils.labels.save(args.ol, labels)
