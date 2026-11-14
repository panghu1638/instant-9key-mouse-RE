# -*- coding: utf-8 -*-
"""
梦幻西游喊话工具 — INSTANT USB GAMING MOUSE (VID 0x30FA)
逆向自 Kenny-Hui/Instant-A704F-Mouse-Utilities + OpenRGB InstantMouseController 协议。

用法:
  python mouse_shout.py bind          # 把侧键绑定成"按键输入动作"(喊话触发键)
  python mouse_shout.py rgbtest      # 闪一下 RGB 验证协议连通
  python mouse_shout.py run          # 监听侧键, 按下即打字+回车喊话
"""
import sys, time, threading, ctypes
import hid

VID = 0x30FA
REPORT_CONFIG = 7   # 07 xx ... 配置通道 (feature report)
REPORT_EVENT  = 6   # 06 BT DP   按键上报 (input report, 2 bytes)

# 物理按键编号 (07 10 BT AT)
BTN_SIDE_BACK, BTN_SIDE_FRONT = 0x04, 0x05   # A704: 04=靠后(朝用户) 05=靠前
# 动作编号 (AT)
ACT_KEYINPUT = 0x00

# ---------------- Windows 打字 (SendInput) ----------------
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
INPUT_MOUSE, INPUT_KEYBOARD = 0, 1
KEYEVENTF_KEYUP, KEYEVENTF_UNICODE = 0x0002, 0x0004
VK_RETURN, VK_CONTROL, VK_TAB = 0x0D, 0x11, 0x09

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]
class _INPUTunion(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("padding", ctypes.c_ubyte * 32)]
class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("union", _INPUTunion)]

def key_tap(vk=None, scan=0, flags=0):
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.union.ki = KEYBDINPUT(vk or 0, scan, flags, 0, None)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

def type_unicode(text, delay=0.01):
    for ch in text:
        code = ord(ch)
        # UTF-16 代理对
        if code > 0xFFFF:
            code -= 0x10000
            pair = [0xD800 + (code >> 10), 0xDC00 + (code & 0x3FF)]
        else:
            pair = [code]
        for c in pair:
            key_tap(scan=c, flags=KEYEVENTF_UNICODE)
            key_tap(scan=c, flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)
        time.sleep(delay)

def tap_vk(vk):
    key_tap(vk=vk); time.sleep(0.02); key_tap(vk=vk, flags=KEYEVENTF_KEYUP)

# ---------------- HID 通道 ----------------
def open_config():
    for info in hid.enumerate(VID, 0):
        if info['interface_number'] == 1 and info['usage_page'] == 0xFF01:
            d = hid.device(); d.open_path(info['path']); return d
    raise RuntimeError('找不到配置通道 (FF01)')

def open_event():
    for info in hid.enumerate(VID, 0):
        if info['interface_number'] == 1 and info['usage_page'] == 0xFF00:
            d = hid.device(); d.open_path(info['path']); return d
    raise RuntimeError('找不到按键上报通道 (FF00)')

def send_cmd(cfg, data):
    """发送 7 字节配置报文 (report id 07)"""
    pkt = bytes([REPORT_CONFIG] + data + [0]*(7-len(data)))
    n = cfg.send_feature_report(pkt)
    if n < 0:
        raise RuntimeError(f'send_feature_report 失败: {hid.error}')

# ---------------- 功能 ----------------
def rgb_test():
    cfg = open_config()
    print('[*] RGB 静态白 3 秒 (07 13 7f 16)...')
    send_cmd(cfg, [0x13, 0x7f, 0x16])
    time.sleep(3)
    print('[*] 恢复慢速呼吸灯 (07 13 7f 10)')
    send_cmd(cfg, [0x13, 0x7f, 0x10])
    cfg.close()
    print('[+] 如果灯变了, 协议连通, 你的鼠标就是这套 Instant 协议!')

def bind_side_button(btn=BTN_SIDE_BACK):
    cfg = open_config()
    send_cmd(cfg, [0x10, btn, ACT_KEYINPUT])
    cfg.close()
    print(f'[+] 已把侧键 0x{btn:02X} 绑定为 Key Input 动作 (07 10 {btn:02X} 00)。')
    print('    拔掉重插鼠标即可恢复默认 (设置不持久)。')

def run_shout(text, btn=BTN_SIDE_BACK, auto_enter=True, open_chat=False):
    cfg, ev = open_config(), open_event()
    ev.set_nonblocking(True)
    threading.Thread(target=lambda: _keepalive(cfg), daemon=True).start()
    print(f'[*] 监听侧键 0x{btn:02X} ... 按下即喊话: "{text}"  (Ctrl+C 退出)')
    while True:
        data = ev.read(8, timeout_ms=200)
        if data and data[0] == REPORT_EVENT and data[1] == btn:
            print('    <侧键按下> 喊话中...')
            if open_chat:
                tap_vk(VK_RETURN); time.sleep(0.3)   # 打开聊天框
            type_unicode(text)
            if auto_enter:
                time.sleep(0.1); tap_vk(VK_RETURN)   # 发送
            time.sleep(0.3)  # 防抖

def _keepalive(cfg):
    while True:
        time.sleep(30)

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'help'
    if cmd == 'bind':
        bind_side_button()
    elif cmd == 'rgbtest':
        rgb_test()
    elif cmd == 'run':
        text = sys.argv[2] if len(sys.argv) > 2 else '世界频道测试喊话~'
        run_shout(text)
    else:
        print(__doc__)
