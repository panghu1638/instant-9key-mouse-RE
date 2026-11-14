# -*- coding: utf-8 -*-
"""
梦幻西游定时喊话器 · 重发模式 (复刻9键鼠标固件行为)
原理: ESC -> ↑(调出上一条消息) -> ENTER(发送)   —— 不打字, 靠重发历史
用法: 先在游戏里手动发一条你要喊的内容, 然后启动本脚本, 游戏保持前台。

  python mouse_timer.py                          # 默认: 2-5分钟随机, 跑2小时
  python mouse_timer.py --min 120 --max 300 --hours 3
  python mouse_timer.py --min 180 --max 300 --hours 2.5 --esc

参数:
  --min    最小间隔秒 (默认 120)
  --max    最大间隔秒 (默认 300)
  --hours  总运行小时 (默认 2)
  --esc    发送前先按 ESC (和鼠标固件一样; 游戏没有弹窗就不用加)
Ctrl+C 随时停止。
"""
import time, random, argparse, ctypes

user32 = ctypes.windll.user32
INPUT_KEYBOARD = 1
KEYUP = 0x0002
VK_ESC, VK_UP, VK_RETURN = 0x1B, 0x26, 0x0D

class KI(ctypes.Structure):
    _fields_ = [('wVk', ctypes.c_ushort), ('wScan', ctypes.c_ushort),
                ('dwFlags', ctypes.c_ulong), ('time', ctypes.c_ulong),
                ('dwExtraInfo', ctypes.c_void_p)]
class INP(ctypes.Structure):
    class U(ctypes.Union):
        _fields_ = [('ki', KI), ('pad', ctypes.c_ubyte * 32)]
    _fields_ = [('type', ctypes.c_ulong), ('u', U)]

def key(vk):
    i = INP(); i.type = INPUT_KEYBOARD
    i.u.ki = KI(vk, 0, 0, 0, None)
    user32.SendInput(1, ctypes.byref(i), ctypes.sizeof(i))
    time.sleep(0.02)
    i.u.ki.dwFlags = KEYUP
    user32.SendInput(1, ctypes.byref(i), ctypes.sizeof(i))

def resend(use_esc):
    if use_esc:
        key(VK_ESC); time.sleep(0.3)
    key(VK_UP)        # ↑ 调出上一条已发送消息
    time.sleep(0.3)
    key(VK_RETURN)    # ENTER 发送
    print(f'    [{time.strftime("%H:%M:%S")}] 已重发上一条', flush=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--min', type=int, default=120)
    ap.add_argument('--max', type=int, default=300)
    ap.add_argument('--hours', type=float, default=2)
    ap.add_argument('--esc', action='store_true')
    a = ap.parse_args()

    total = a.hours * 3600
    start = time.time()
    est = int(total / ((a.min + a.max) / 2))
    print(f'[*] 定时重发喊话: 每 {a.min}-{a.max} 秒随机一条, 共 {a.hours} 小时, 预计约 {est} 条')
    print(f'    连招: {"ESC -> " if a.esc else ""}↑ -> ENTER   (3 秒后开始, 请切到游戏窗口!)')
    time.sleep(3)
    n = 0
    try:
        while (elapsed := time.time() - start) < total:
            wait = random.randint(a.min, a.max)
            left = total - elapsed
            print(f'[{time.strftime("%H:%M:%S")}] 已发 {n} 条 | 剩余 {left/60:.0f} 分钟 | 下一条 {wait}s 后')
            time.sleep(min(wait, left + 1))
            if time.time() - start >= total:
                break
            resend(a.esc)
            n += 1
    except KeyboardInterrupt:
        print('\n[!] 手动停止')
    print(f'[+] 完成: 共发送 {n} 条, 运行 {(time.time()-start)/60:.1f} 分钟')

if __name__ == '__main__':
    main()
