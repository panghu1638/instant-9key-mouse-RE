# -*- coding: utf-8 -*-
"""
Instant 鼠标 (VID 30FA) 全功能控制台 — 逆向协议完整实现
协议来源: OpenRGB InstantMouseController + Kenny-Hui/Instant-A704F 本地 diff 验证

用法:
  python mouse_ctl.py export [文件]     # 导出当前模式 -> JSON (固件读回 + 会话配置)
  python mouse_ctl.py import <文件>     # 从 JSON 恢复全部设置
  python mouse_ctl.py dpi <档0-3> <dpi值> [启用掩码hex]   # 例: dpi 1 1600 0f
  python mouse_ctl.py bind <按键> <动作>                  # bind side_back key
  python mouse_ctl.py light <模式> [颜色RRGGBB]           # off/static/breath/rainbow...
  python mouse_ctl.py scroll <normal|volume|off>
  python mouse_ctl.py fire <毫秒>                        # 连发间隔 8-2000ms
  python mouse_ctl.py type <文本>                        # 模拟键盘输入(喊话核心)
  python mouse_ctl.py media <key>                        # volume_up/volume_down/play/mute...
  python mouse_ctl.py status                             # 读回固件状态
"""
import sys, json, time, os
import hid

VID = 0x30FA
REPORT = 7

BUTTONS = {'left':0x01,'right':0x02,'middle':0x03,'side_back':0x04,'side_front':0x05,
           'mid_back':0x06,'mid_front':0x08}
ACTIONS = {'key':0x00,'lclick':0x01,'mclick':0x02,'rclick':0x03,'back':0x04,'forward':0x05,
           'dpi_cycle':0x06,'show_desktop':0x07,'double_click':0x08,'fire':0x09,
           'dpi+':0x0a,'dpi-':0x0b}
LIGHTS  = {'breath_6s':0x10,'breath_5s':0x11,'breath_4s':0x12,'breath_3s':0x13,
           'breath_2s':0x14,'breath_1s':0x15,'static':0x16,'off':0x17}
SCROLLS = {'normal':0x00,'volume':0x01,'off':0x02}
MEDIA   = {'volume_down':0x00ea,'volume_up':0x00e9,'browser':0x0223,'player':0x0183,
           'mail':0x018a,'prev':0x00b6,'next':0x00b5,'mute':0x00e2,'play':0x00cd,
           'calc':0x0192}

# ---------------- 底层 ----------------
def open_cfg():
    for info in hid.enumerate(VID, 0):
        if info['interface_number'] == 1 and info['usage_page'] == 0xFF01:
            d = hid.device(); d.open_path(info['path']); return d
    raise RuntimeError('找不到配置通道 (FF01)')

def send(cfg, data):
    cfg.send_feature_report(bytes([REPORT] + data + [0]*(7-len(data))))
    time.sleep(0.12)

def read_state(cfg):
    return bytes(cfg.get_feature_report(REPORT, 16)[1:])

def decode_state(b):
    return {
        'raw_hex': b.hex(' '),
        'rgb_mode': f'0x{b[7]:02X}',
        'rgb_mode_name': {v: k for k, v in LIGHTS.items()}.get(b[7], 'unknown'),
        'active_dpi_stage': b[8] // 2,
        'fw_fields': {'b1_4': b[1:5].hex(), 'b5': f'0x{b[5]:02X}',
                      'b6': f'0x{b[6]:02X}', 'b10': f'0x{b[10]:02X}', 'b14': f'0x{b[14]:02X}'},
    }

# ---------------- 高层命令 ----------------
def cmd_dpi(cfg, stage, dpi, enable=0x0F):
    # DP: 高4位=DPI值(×200), 低4位=档位槽; EP: 启用的档位掩码
    dp = ((dpi // 200) << 4) | (stage & 0x0F)
    send(cfg, [0x09, stage & 0xFF, dp, enable & 0xFF])

def cmd_bind(cfg, button, action):
    send(cfg, [0x10, button, action])

def cmd_scroll(cfg, mode):
    send(cfg, [0x11, mode, 0x00])

def cmd_fire(cfg, ms):
    ms = max(8, min(2000, int(ms)))
    send(cfg, [0x12, 0x00, ms & 0xFF])

def cmd_light(cfg, mode):
    send(cfg, [0x13, 0x7F, mode])

def cmd_type_keys(cfg, keycodes):
    # keycodes: 最多6个 HID 键码
    send(cfg, [0x15] + list(keycodes[:6]) + [0]*(6-len(keycodes)))

def cmd_media(cfg, usage16):
    send(cfg, [0x17, (usage16 >> 8) & 0xFF, usage16 & 0xFF])

# ---------------- 导出 / 导入 ----------------
def do_export(path):
    cfg = open_cfg()
    state = decode_state(read_state(cfg))
    profile_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mouse_profile.json')
    session = {}
    if os.path.exists(profile_path):
        session = json.load(open(profile_path, encoding='utf-8'))
    out = {
        'device': {'vid': VID, 'name': 'INSTANT USB GAMING MOUSE', 'protocol': 'Instant A70x'},
        'exported_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'firmware_state': state,          # 从固件读回的真实状态
        'session_settings': session,      # 本工具会话应用的配置
    }
    json.dump(out, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    cfg.close()
    print(f'[+] 已导出到 {path}')
    print(json.dumps(state, ensure_ascii=False, indent=2))

def do_import(path):
    data = json.load(open(path, encoding='utf-8'))
    cfg = open_cfg()
    s = data.get('session_settings', {})
    n = 0
    for b in s.get('bindings', []):
        cmd_bind(cfg, b['button'], b['action']); n += 1
    if 'scroll' in s: cmd_scroll(cfg, s['scroll']); n += 1
    if 'fire_ms' in s: cmd_fire(cfg, s['fire_ms']); n += 1
    if 'light' in s: cmd_light(cfg, s['light']); n += 1
    for i, (stage, dpi, mask) in enumerate(s.get('dpi', [])):
        cmd_dpi(cfg, stage, dpi, mask); n += 1
    cfg.close()
    print(f'[+] 已从 {path} 恢复 {n} 项设置')

def record(key, value):
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mouse_profile.json')
    prof = {}
    if os.path.exists(p):
        prof = json.load(open(p, encoding='utf-8'))
    prof.setdefault(key, [])
    if key == 'bindings':
        prof[key] = [b for b in prof[key] if b.get('button') != value.get('button')]
    prof[key].append(value) if isinstance(value, dict) else prof.__setitem__(key, value)
    if not isinstance(value, dict) and key != 'bindings':
        prof[key] = value
    json.dump(prof, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

# ---------------- Windows SendInput (打字) ----------------
def _sendinput_text(text, delay=0.01):
    import ctypes
    u32 = ctypes.windll.user32
    KEYUP, UNI = 0x0002, 0x0004
    class KI(ctypes.Structure):
        _fields_ = [('wVk', ctypes.c_ushort), ('wScan', ctypes.c_ushort),
                    ('dwFlags', ctypes.c_ulong), ('time', ctypes.c_ulong),
                    ('dwExtraInfo', ctypes.c_void_p)]
    class INP(ctypes.Structure):
        class U(ctypes.Union):
            _fields_ = [('ki', KI), ('pad', ctypes.c_ubyte * 32)]
        _fields_ = [('type', ctypes.c_ulong), ('u', U)]
    def tap(scan, up=False):
        i = INP(); i.type = 1
        i.u.ki = KI(0, scan, UNI | (KEYUP if up else 0), 0, None)
        u32.SendInput(1, ctypes.byref(i), ctypes.sizeof(i))
    for ch in text:
        for c in ([ord(ch)] if ord(ch) <= 0xFFFF else
                  [0xD800 + ((ord(ch)-0x10000) >> 10), 0xDC00 + ((ord(ch)-0x10000) & 0x3FF)]):
            tap(c); tap(c, up=True)
        time.sleep(delay)

# ---------------- CLI ----------------
def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); return
    cmd = a[0]
    if cmd == 'export':
        do_export(a[1] if len(a) > 1 else 'mouse_mode_export.json'); return
    if cmd == 'import':
        do_import(a[1]); return
    cfg = open_cfg()
    if cmd == 'status':
        print(json.dumps(decode_state(read_state(cfg)), ensure_ascii=False, indent=2))
    elif cmd == 'dpi' and len(a) >= 3:
        stage, dpi = int(a[1]), int(a[2])
        mask = int(a[3], 16) if len(a) > 3 else 0x0F
        cmd_dpi(cfg, stage, dpi, mask)
        record('dpi', [stage, dpi, mask]); print(f'[+] 档{stage} = {dpi} DPI, 启用掩码 0x{mask:02X}')
    elif cmd == 'bind' and len(a) == 3:
        b, act = BUTTONS[a[1]], ACTIONS[a[2]]
        cmd_bind(cfg, b, act)
        record('bindings', {'button': b, 'action': act})
        print(f'[+] {a[1]}(0x{b:02X}) -> {a[2]}(0x{act:02X})')
    elif cmd == 'light' and len(a) >= 2:
        m = LIGHTS[a[1]] if a[1] in LIGHTS else int(a[1], 16)
        cmd_light(cfg, m); record('light', m)
        print(f'[+] 灯效 -> {a[1]} (0x{m:02X})')
    elif cmd == 'scroll' and len(a) == 2:
        cmd_scroll(cfg, SCROLLS[a[1]]); record('scroll', SCROLLS[a[1]])
        print(f'[+] 滚轮 -> {a[1]}')
    elif cmd == 'fire' and len(a) == 2:
        cmd_fire(cfg, int(a[1])); record('fire_ms', int(a[1]))
        print(f'[+] 连发间隔 -> {a[1]}ms')
    elif cmd == 'type' and len(a) == 2:
        _sendinput_text(a[1])
        print(f'[+] 已模拟键盘输入: {a[1]}')
    elif cmd == 'media' and len(a) == 2:
        cmd_media(cfg, MEDIA[a[1]]); print(f'[+] 多媒体键 -> {a[1]}')
    else:
        print('参数错误'); print(__doc__)
    cfg.close()

if __name__ == '__main__':
    main()
