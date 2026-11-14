# -*- coding: utf-8 -*-
import hid

for info in hid.enumerate(0x30FA, 0):
    d = hid.device()
    try:
        d.open_path(info['path'])
    except Exception as e:
        print('open fail', info['interface_number'], hex(info['usage_page']), e)
        continue
    tag = f"int{info['interface_number']} pg{info['usage_page']:04X}"
    print(tag, 'opened')
    try:
        data = d.read(64, timeout_ms=800)
        print('  blocking read ok:', bytes(data).hex() if data else '(timeout)')
    except Exception as e:
        print('  blocking read FAIL:', type(e).__name__, e)
    try:
        d.set_nonblocking(True)
        try:
            data = d.read(64)
            print('  nonblocking ok:', bytes(data).hex() if data else '(empty)')
        except Exception as e:
            print('  nonblocking FAIL:', type(e).__name__, e)
        d.set_nonblocking(False)
    except Exception as e:
        print('  set_nonblocking FAIL:', e)
    try:
        print('  hid.error():', d.error())
    except Exception as e:
        print('  error() fail:', e)
    d.close()
