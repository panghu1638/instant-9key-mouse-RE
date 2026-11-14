# -*- coding: utf-8 -*-
"""探测 Instant 鼠标 (30FA) 的配置读回能力, 并 dump 各通道当前缓冲。"""
import hid, time

VID = 0x30FA

def open_cfg():
    for info in hid.enumerate(VID, 0):
        if info['interface_number'] == 1 and info['usage_page'] == 0xFF01:
            d = hid.device(); d.open_path(info['path']); return d

def open_evt():
    for info in hid.enumerate(VID, 0):
        if info['interface_number'] == 1 and info['usage_page'] == 0xFF00:
            d = hid.device(); d.open_path(info['path']); return d

cfg = open_cfg()

print('=== 各 report id 的 GET_FEATURE 读回 (report 1..9) ===')
for rid in range(1, 10):
    try:
        data = cfg.get_feature_report(rid, 16)
        print(f'  report {rid}: {bytes(data).hex()}')
    except Exception as e:
        print(f'  report {rid}: err {e}')

print()
print('=== 读回变化测试: 修改 DPI (07 09 01 88 0f) 前后对比 report 7 ===')
before = bytes(cfg.get_feature_report(7, 16)).hex()
cfg.send_feature_report(bytes([7, 0x09, 0x01, 0x88, 0x0f, 0, 0, 0]))
time.sleep(0.2)
after = bytes(cfg.get_feature_report(7, 16)).hex()
print(f'  before: {before}')
print(f'  after : {after}')
print(f'  变化: {"无 (write-only)" if before == after else "有! 设备支持读回"}')

print()
print('=== FF00 事件通道: 短窗口读取 (现在按几下侧键试试) ===')
ev = open_evt()
ev.set_nonblocking(True)
deadline = time.time() + 5
seen = []
while time.time() < deadline:
    data = ev.read(8, timeout_ms=200)
    if data:
        seen.append(bytes(data).hex())
if seen:
    for s in seen: print('  事件:', s)
else:
    print('  (5 秒内无按键事件)')
cfg.close()
