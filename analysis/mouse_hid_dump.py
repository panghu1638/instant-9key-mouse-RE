# -*- coding: utf-8 -*-
"""Enumerate VID 0x30FA (wired gaming mouse) HID interfaces and dump report descriptors."""
import hid

VID = 0x30FA

def decode_rd(desc):
    """Minimal HID report descriptor decoder for common items."""
    i = 0
    out = []
    while i < len(desc):
        b = desc[i]
        if b == 0xFE:  # long item
            size = desc[i+1]; tag = desc[i+2]
            i += 2 + size
            continue
        size = b & 0x03
        if size == 3: size = 4
        tag = (b >> 4) & 0x0F
        typ = (b >> 2) & 0x03  # 0 main,1 global,2 local
        i += 1
        val = int.from_bytes(desc[i:i+size], 'little', signed=True)
        raw = bytes(desc[i:i+size]).hex()
        i += size
        main = {8:'Input',9:'Output',0xB:'Feature',0:'Usage Page?'}
        glob = {0:'Usage Page',1:'Logical Min',2:'Logical Max',3:'Phys Min',4:'Phys Max',
                5:'Unit Exp',6:'Unit',7:'Report Size',8:'Report ID',9:'Report Count',
                0xA:'Push',0xB:'Pop'}
        loc = {0:'Usage',1:'Usage Min',2:'Usage Max',9:'Delim'}
        if typ == 0:
            name = main.get(tag, f'Main_{tag:02X}')
            extra = ''
            if tag == 8:  # Input
                bits = []
                flags = ['Data/Const','Array/Var','Abs/Rel','NoWrap/Wrap','Lin/NonLin',
                         'Pref/NoPref','NoNull/Null','','BitField/Buffered']
                for n,f in enumerate(flags[:8]):
                    if f and (val >> n) & 1: bits.append(f.split('/')[1])
                extra = ' ' + '/'.join(bits) if bits else ' Const'
            out.append(f"{name}{extra} {hex(val & 0xFFFFFFFF) if size else ''} [{raw}]")
        elif typ == 1:
            out.append(f"  {glob.get(tag, f'Glob_{tag:02X}')} = {val} [{raw}]")
        else:
            out.append(f"  {loc.get(tag, f'Loc_{tag:02X}')} = {hex(val & 0xFFFFFFFF)} [{raw}]")
    return '\n'.join(out)

for info in hid.enumerate(VID, 0):
    print('='*70)
    print(f"path      : {info['path']}")
    print(f"interface : {info['interface_number']}")
    print(f"usage_page: 0x{info['usage_page']:04X}  usage: 0x{info['usage']:04X}")
    try:
        print(f"manufacturer: {info['manufacturer_string']!r}")
        print(f"product     : {info['product_string']!r}")
        print(f"serial      : {info['serial_number']!r}")
        print(f"version     : {info['release_number']}")
    except Exception as e:
        print('strings:', e)
    try:
        d = hid.device()
        d.open_path(info['path'])
        rd = d.get_report_descriptor()
        print(f"--- report descriptor ({len(rd)} bytes) ---")
        print(decode_rd(rd))
        d.close()
    except Exception as e:
        print('desc read failed:', e)
