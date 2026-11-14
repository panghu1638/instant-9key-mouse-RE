# -*- coding: utf-8 -*-
"""
9键鼠标 最终版监听: RawInput(鼠标+键盘) + hidapi(多媒体+私有通道)
"""
import hid, time, threading, ctypes
from ctypes import wintypes

VID = 0x30FA
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# ---------- Raw Input ----------
WM_INPUT = 0x00FF
RIDEV_INPUTSINK = 0x00000100
RIDEV_REMOVE = 0x00000001
RID_INPUT = 0x10000003

class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [('usUsagePage', wintypes.USHORT), ('usUsage', wintypes.USHORT),
                ('dwFlags', wintypes.DWORD), ('hwndTarget', wintypes.HWND)]

class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [('dwType', wintypes.DWORD), ('dwSize', wintypes.DWORD),
                ('hDevice', wintypes.HANDLE), ('wParam', wintypes.WPARAM)]

class RAWKEYBOARD(ctypes.Structure):
    _fields_ = [('MakeCode', wintypes.USHORT), ('Flags', wintypes.USHORT),
                ('Reserved', wintypes.USHORT), ('VKey', wintypes.USHORT),
                ('Message', wintypes.UINT), ('ExtraInformation', wintypes.ULONG)]

class RAWMOUSE(ctypes.Structure):
    class U(ctypes.Union):
        class S(ctypes.Structure):
            _fields_ = [('usButtonFlags', wintypes.USHORT), ('usButtonData', wintypes.USHORT)]
        _fields_ = [('ulButtons', wintypes.ULONG), ('s', S)]
    _anonymous_ = ('u',)
    _fields_ = [('usFlags', wintypes.USHORT), ('u', U), ('ulRawButtons', wintypes.ULONG),
                ('lLastX', wintypes.LONG), ('lLastY', wintypes.LONG),
                ('ulExtraInformation', wintypes.ULONG)]

class RAWINPUT(ctypes.Structure):
    class D(ctypes.Union):
        _fields_ = [('mouse', RAWMOUSE), ('keyboard', RAWKEYBOARD), ('pad', ctypes.c_ubyte * 40)]
    _anonymous_ = ('d',)
    _fields_ = [('header', RAWINPUTHEADER), ('d', D)]

BTN_NAMES = {1:'左键DOWN',2:'左键UP',4:'右键DOWN',8:'右键UP',16:'中键DOWN',32:'中键UP',
             64:'侧键1DOWN',128:'侧键1UP',256:'侧键2DOWN',512:'侧键2UP',1024:'滚轮'}
VK_NAMES = {0x0D:'ENTER',0x1B:'ESC',0x08:'BACKSPACE',0x09:'TAB',0x20:'SPACE',
            0x30:'0',0x31:'1',0x32:'2',0x33:'3',0x34:'4',0x35:'5',0x36:'6',0x37:'7',0x38:'8',0x39:'9',
            0x41:'A',0x42:'B',0x43:'C',0x44:'D',0x45:'E',0x46:'F',0x47:'G',0x48:'H',0x49:'I',
            0x4A:'J',0x4B:'K',0x4C:'L',0x4D:'M',0x4E:'N',0x4F:'O',0x50:'P',0x51:'Q',0x52:'R',
            0x53:'S',0x54:'T',0x55:'U',0x56:'V',0x57:'W',0x58:'X',0x59:'Y',0x5A:'Z',
            0xBA:';',0xBB:'=',0xBC:',',0xBD:'-',0xBE:'.',0xBF:'/',0xC0:'`',
            0xDB:'[',0xDC:'\\',0xDD:']',0xDE:"'",0xAD:'媒体键',0xA6:'浏览器回退',0xA7:'浏览器前进'}

def raw_thread():
    LRESULT = ctypes.c_ssize_t
    WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t)
    def wndproc(h, msg, wp, lp):
        if msg == WM_INPUT:
            size = wintypes.UINT()
            user32.GetRawInputData(lp, RID_INPUT, None, ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER))
            buf = (ctypes.c_ubyte * size.value)()
            user32.GetRawInputData(lp, RID_INPUT, buf, ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER))
            ri = ctypes.cast(buf, ctypes.POINTER(RAWINPUT)).contents
            ts = time.strftime('%H:%M:%S')
            if ri.header.dwType == 1:  # keyboard
                k = ri.keyboard
                if not (k.Flags & 2):  # down only
                    if k.VKey == 0xE7 or k.VKey == 0xFF:  # VK_PACKET = Unicode 注入字符
                        try:
                            ch = chr(k.MakeCode)
                            print(f'[{ts}] Unicode字  U+{k.MakeCode:04X} = "{ch}"', flush=True)
                        except Exception:
                            print(f'[{ts}] Unicode字  U+{k.MakeCode:04X}', flush=True)
                    else:
                        name = VK_NAMES.get(k.VKey, f'VK_{k.VKey:02X}')
                        print(f'[{ts}] Raw键盘   VK={name} 扫描码=0x{k.MakeCode:02X}', flush=True)
            elif ri.header.dwType == 0:  # mouse
                m = ri.mouse
                f = m.s.usButtonFlags if hasattr(m, 's') else 0
                if f:
                    names = [n for v, n in BTN_NAMES.items() if f & v and 'UP' not in n and v != 1024]
                    if names:
                        print(f'[{ts}] Raw鼠标   -> {",".join(names)}', flush=True)
                elif f & 1024:
                    print(f'[{ts}] Raw鼠标   -> 滚轮 {ctypes.c_short(m.s.usButtonData).value}', flush=True)
        return 0
    wc = WNDPROC(wndproc)
    class WNDCLASS(ctypes.Structure):
        _fields_ = [('style', wintypes.UINT), ('lpfnWndProc', WNDPROC),
                    ('cbClsExtra', ctypes.c_int), ('cbWndExtra', ctypes.c_int),
                    ('hInstance', wintypes.HANDLE), ('hIcon', wintypes.HANDLE),
                    ('hCursor', wintypes.HANDLE), ('hbrBackground', wintypes.HANDLE),
                    ('lpszMenuName', wintypes.LPCWSTR), ('lpszClassName', wintypes.LPCWSTR)]
    wcx = WNDCLASS()
    wcx.lpfnWndProc = wc
    wcx.lpszClassName = 'MouseSniff'
    user32.RegisterClassW(ctypes.byref(wcx))
    hwnd = user32.CreateWindowExW(0, 'MouseSniff', 'x', 0, 0, 0, 0, 0, None, None, None, None)
    rid = (RAWINPUTDEVICE * 2)(
        RAWINPUTDEVICE(1, 2, RIDEV_INPUTSINK, hwnd),   # 鼠标
        RAWINPUTDEVICE(1, 6, RIDEV_INPUTSINK, hwnd),   # 键盘
    )
    if not user32.RegisterRawInputDevices(rid, 2, ctypes.sizeof(RAWINPUTDEVICE)):
        print('[!] RegisterRawInputDevices 失败', kernel32.GetLastError())
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))

# ---------- hidapi 通道 ----------
CONSUMER = {0xe2:'静音',0xe9:'音量+',0xea:'音量-',0xb5:'下一曲',0xb6:'上一曲',0xcd:'播放/暂停',
            0x223:'浏览器主页',0x183:'播放器',0x18a:'邮件',0x192:'计算器'}

def hid_thread():
    handles = []
    for info in hid.enumerate(VID, 0):
        if info['interface_number'] == 1 and info['usage_page'] in (0x000C, 0xFF00):
            try:
                d = hid.device(); d.open_path(info['path']); d.set_nonblocking(True)
                handles.append((d, info['usage_page']))
            except Exception as e:
                print('[!] hidapi 打开失败:', e)
    while True:
        for d, page in handles:
            try:
                data = d.read(64, timeout_ms=50)
            except Exception:
                continue
            if data:
                ts = time.strftime('%H:%M:%S')
                if data[0] == 2:
                    u = data[1] | data[2] << 8
                    print(f'[{ts}] HID多媒体 usage=0x{u:04X} ({CONSUMER.get(u, "?")})', flush=True)
                elif data[0] == 6:
                    print(f'[{ts}] HID私有   键=0x{data[1]:02X} 参数=0x{data[2]:02X}', flush=True)
                else:
                    print(f'[{ts}] HID其他   {bytes(data).hex(" ")}', flush=True)

threading.Thread(target=raw_thread, daemon=True).start()
print('[*] RawInput + hidapi 监听启动, 按 1-9 号键吧', flush=True)
hid_thread()
