# -*- coding: utf-8 -*-
"""逐条命令 diff 实验: 建立 写入命令 -> 读回缓冲变化 的映射表。"""
import hid, time

VID = 0x30FA
CFG_REPORT = 7

def open_cfg():
    for info in hid.enumerate(VID, 0):
        if info['interface_number'] == 1 and info['usage_page'] == 0xFF01:
            d = hid.device(); d.open_path(info['path']); return d

cfg = open_cfg()

def rd():
    return list(cfg.get_feature_report(CFG_REPORT, 16))[1:]  # 去掉 report id

def send(data):
    cfg.send_feature_report(bytes([CFG_REPORT] + data + [0]*(7-len(data))))
    time.sleep(0.15)

base = rd()
print(f'基线: {bytes(base).hex(" ")}')
print()

tests = [
    ('绑键: 侧后=KeyInput',      [0x10, 0x04, 0x00]),
    ('绑键: 侧前=前进(0x05)',    [0x10, 0x05, 0x05]),
    ('滚轮: 音量模式',           [0x11, 0x01, 0x00]),
    ('滚轮: 正常模式',           [0x11, 0x00, 0x00]),
    ('连发速度=0x32',            [0x12, 0x00, 0x32]),
    ('灯: 静态',                 [0x13, 0x7f, 0x16]),
    ('灯: 呼吸慢',               [0x13, 0x7f, 0x10]),
    ('DPI: 3档 800 (09 00 84)',  [0x09, 0x00, 0x84, 0x00]),
    ('DPI: 1档 1600 (09 00 8b)', [0x09, 0x00, 0x8b, 0x00]),
    ('DPI: 档2 800  (09 01 84)', [0x09, 0x01, 0x84, 0x00]),
    ('键盘输入: 释放',           [0x15, 0,0,0,0,0,0]),
]

state = base
for name, cmd in tests:
    send(cmd)
    new = rd()
    diffs = [i for i in range(len(state)) if state[i] != new[i]]
    if diffs:
        d = ' '.join(f'[{i}]{state[i]:02X}->{new[i]:02X}' for i in diffs)
        print(f'{name:24s} => {d}')
    else:
        print(f'{name:24s} => (读回无变化)')
    state = new

print()
print(f'实验后状态: {bytes(state).hex(" ")}')
cfg.close()
