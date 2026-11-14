# -*- coding: utf-8 -*-
"""9键鼠标监听 终极版: 低级钩子(键盘+鼠标) + hidapi(私有/多媒体通道)"""
import hid, time, threading, ctypes
from datetime import datetime
from ctypes import wintypes

VID = 0x30FA
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WH_KEYBOARD_LL, WH_MOUSE_LL = 13, 14
WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP = 0x100, 0x101, 0x104, 0x105

VK_NAMES = {0x0D:'ENTER',0x1B:'ESC',0x08:'BACKSPACE',0x09:'TAB',0x20:'SPACE',
            0x11:'CTRL',0x10:'SHIFT',0x12:'ALT',0x5B:'WIN',
            0xE7:'VK_PACKET(Unicode)'}
for i in range(0x30, 0x3A): VK_NAMES[i] = chr(i)
for i in range(0x41, 0x5B): VK_NAMES[i] = chr(i)
VK_NAMES.update({0xBA:';',0xBB:'=',0xBC:',',0xBD:'-',0xBE:'.',0xBF:'/',0xC0:'`',
                 0xDB:'[',0xDC:'\\',0xDD:']',0xDE:"'",0xAD:'媒体'})
MOUSE_BTN = {0x01:'左键',0x02:'右键',0x10:'中键',0x20:'侧键1',0x40:'侧键2'}

HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
PMSG = ctypes.POINTER(wintypes.MSG)

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [('vkCode', wintypes.DWORD), ('scanCode', wintypes.DWORD),
                ('flags', wintypes.DWORD), ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.POINTER(ctypes.c_ulong))]

class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [('pt', wintypes.POINT), ('mouseData', wintypes.DWORD),
                ('flags', wintypes.DWORD), ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.POINTER(ctypes.c_ulong))]

kb_hook = ms_hook = None

def kbd_proc(n, wp, lp):
    k = ctypes.cast(lp, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
    ts = datetime.now().strftime('%H:%M:%S')
    if wp in (WM_KEYDOWN, WM_SYSKEYDOWN):
        if k.vkCode == 0xE7:  # Unicode 注入
            try: ch = chr(k.scanCode)
            except Exception: ch = '?'
            print(f'[{ts}] 注入字符 U+{k.scanCode:04X} = "{ch}"', flush=True)
        else:
            inj = ' [注入]' if k.flags & 0x10 else ''
            print(f'[{ts}] 键盘DOWN  {VK_NAMES.get(k.vkCode, f"VK_{k.vkCode:02X}")}{inj}', flush=True)
    return user32.CallNextHookEx(None, n, wp, lp)

def ms_proc(n, wp, lp):
    m = ctypes.cast(lp, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
    ts = datetime.now().strftime('%H:%M:%S')
    if wp == 0x201:   print(f'[{ts}] 鼠标DOWN  左键', flush=True)
    elif wp == 0x204: print(f'[{ts}] 鼠标DOWN  右键', flush=True)
    elif wp == 0x207: print(f'[{ts}] 鼠标DOWN  中键', flush=True)
    elif wp == 0x20B:
        hi = (m.mouseData >> 16) & 0xFFFF
        print(f'[{ts}] 鼠标DOWN  XBUTTON {hi} (侧键1/2)', flush=True)
    elif wp == 0x20A:
        d = ctypes.c_short(m.mouseData >> 16).value
        print(f'[{ts}] 鼠标滚轮  {d}', flush=True)
    return user32.CallNextHookEx(None, n, wp, lp)

def hook_thread():
    global kb_hook, ms_hook
    global kb_cb, ms_cb   # 回调对象必须保活, 否则被GC后调用即崩溃
    kb_cb = HOOKPROC(kbd_proc)
    ms_cb = HOOKPROC(ms_proc)
    user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t, ctypes.c_ssize_t]
    kb_hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, kb_cb, None, 0)
    ms_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, ms_cb, None, 0)
    if not kb_hook or not ms_hook:
        print('[!] 钩子注册失败', kernel32.GetLastError())
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        pass

CONSUMER = {0xe2:'静音',0xe9:'音量+',0xea:'音量-',0xb5:'下一曲',0xb6:'上一曲',0xcd:'播放/暂停'}

def hid_thread():
    handles = []
    for info in hid.enumerate(VID, 0):
        if info['interface_number'] == 1 and info['usage_page'] in (0x000C, 0xFF00):
            try:
                d = hid.device(); d.open_path(info['path']); d.set_nonblocking(True)
                handles.append((d, info['usage_page']))
            except Exception as e:
                print('[!] hidapi 打开失败:', e, flush=True)
    while True:
        for d, page in handles:
            try:
                data = d.read(64, timeout_ms=50)
            except Exception:
                continue
            if data:
                ts = datetime.now().strftime('%H:%M:%S')
                if data[0] == 6:
                    print(f'[{ts}] HID私有   键=0x{data[1]:02X} 参数=0x{data[2]:02X}', flush=True)
                elif data[0] == 2:
                    u = data[1] | data[2] << 8
                    print(f'[{ts}] HID多媒体 usage=0x{u:04X} ({CONSUMER.get(u,"?")})', flush=True)
                else:
                    print(f'[{ts}] HID其他   {bytes(data).hex(" ")}', flush=True)

print('[*] 终极监听启动: 低级钩子 + HID通道。按 1-9 号键', flush=True)
threading.Thread(target=hook_thread, daemon=True).start()
hid_thread()


