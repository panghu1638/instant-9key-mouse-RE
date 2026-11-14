# INSTANT 9键游戏鼠标 逆向工程资料

> 目标设备: "USB GAMING MOUSE" (USB VID `30FA` PID `1340`)
> 芯片方案: 无锡瞬电 Instant Microelectronics A70x 系 (INSTANT)
> 同方案设备: VGN/ATK/VXE 部分型号、Anko、各种白牌"梦幻西游喊话鼠标"
> 分析日期: 2026-11-14 ~ 2026-11-15 (Windows 11, 全部实测验证)

---

## 一、设备枚举

```
USB VID:PID = 30FA:1340  (bus-reported: "USB GAMING MOUSE", 厂商字符串: INSTANT)
复合设备, 2 个 USB 接口:
  接口 0: 标准鼠标 (Usage Page 0x0001 / Usage 0x0002)
  接口 1: 复合 HID, 5 个 Collection:
    COL01  键盘       (Page 0x0001, Usage 0x0006, Report ID 3, 6KRO)
    COL02  消费者控制 (Page 0x000C, Report ID 2, 16-bit usage 0-668)
    COL03  厂商输入   (Page 0xFF00, Report ID 6, 2 字节)   ← 按键事件上报
    COL04  厂商配置   (Page 0xFF01, Report ID 7, 7 字节 Feature) ← 配置命令
    COL05  系统控制   (Page 0x0001, Usage 0x0080, Report ID 8)
```

## 二、配置协议 (写入: Feature Report ID 0x07, 接口1/COL04)

报文格式: `[0x07, 命令, 参数..., 0x00 填充]` 共 8 字节 (1 字节 Report ID + 7 字节负载)

| 命令 | 功能 | 格式 |
|---|---|---|
| `07 09 AD DP EP` | DPI 配置 | AD=活动档(0-3); DP 高4位=DPI值(×200), 低4位=档位槽; EP=启用档位掩码 |
| `07 10 BT AT` | 按键绑定 | BT=物理键(下表), AT=动作(下表) |
| `07 11 SC DB` | 滚轮模式 | SC: 00正常 01音量 02关闭/调试; DB=调试动作码 |
| `07 12 00 FR` | 连发速度 | FR=连发间隔 8ms-2000ms |
| `07 13 7F CF` | RGB 模式 | CF: 10-15=呼吸(6s→1s), 16=常亮, 17=关闭 |
| `07 14 XG RB` | RGB 颜色 | X=DPI档, 4bit/通道 (OpenRGB InstantMouseController) |
| `07 15 K1..K6` | 模拟键盘输入 | 最多 6 个 HID 键码同时按下, 全 00 = 释放 |
| `07 17 MKH MKL` | 多媒体键 | 16-bit Consumer Page usage (大端) |

### 物理按键编号 (BT)
```
01=左键  02=右键  03=中键  04=侧后  05=侧前  06=中后  08=中前
(上报事件里为 0xF1-0xF8, 见下)
```

### 动作编号 (AT)
```
00=按键输入  01=左键  02=中键  03=右键  04=后退  05=前进
06=DPI循环  07=显示桌面  08=双击  09=连发(Fire)  0A=DPI+  0B=DPI-
```

## 三、状态读回 (GET_FEATURE Report ID 0x07, 16 字节)

设备支持配置读回! (这一项是社区已公开资料中没有的, 本地 diff 实验发现)

```
字节布局 (payload 15 字节):
[0]  状态 00
[1-4] 固件特征 (实测 56 09 22 00)
[5]  固件特征 0x23
[6]  0x10
[7]  当前 RGB 模式 (与 0x13 命令的 CF 一致, 实测 0x10↔0x13↔0x16 随写入变化)
[8]  当前活动 DPI 档位 × 2 (AD=0→00, 1→02, 2→04, 3→06, 实测验证)
[9]  00
[10] 0x6D
[11-13] 00
[14] 0x02
```
注: DPI 数值与按键绑定表不进读回缓冲 (只写)。

## 四、事件上报 (Input Report, 接口1/COL03)

```
06 BT DP   按键事件
  BT: F1=左键 F2=中键 F3=右键 F4=侧后 F5=侧前 F6=中后 F8=中前
  另发现 0xF9 (本 9 键鼠标的扩展键, 社区文档未记载)
  DP: 按下=配置槽编号(01/02/03 轮换), 松开=0x80
02 KY KY   多媒体键事件
```

## 五、9 键"自动喊话"固件行为 (Raw Input + LL Hook 实测)

商品名"9键鼠标-自动喊话(普普通版)"的固件连招, 全部为模拟标准键盘事件:

```
单号随机喊 (4号键):  Alt+Shift -> ESC -> ↑ -> ENTER   (每 10-24 秒随机循环)
                    ↑ = 聊天框调出上一条已发送消息, ENTER 重发
                    固件不存储喊话内容! 内容=游戏聊天框最后一条
多号同时喊 (5/6/7):  右Ctrl+TAB (切换游戏窗口) -> ↑ -> ENTER, 逐窗口执行
打字喊话 (8号键):    通过 IME 拼音逐字注入 (实测 H A O L 空格 ENTER)
连点 (3号键):        自动左键连点, 实测约 13-14 次/秒, 开关式
```

## 六、Windows 平台开发注意事项 (踩坑记录)

- hidapi **读不到**鼠标/键盘类 HID Collection (int0 / 键盘COL) — Windows 拒绝,
  需用 Raw Input 或 Low-Level Hook; 厂商 Page (FF00/FF01) 和 Consumer Page 正常
- LL Hook 回调对象必须保活 (ctypes 临时对象被 GC 后调用即崩溃)
- G HUB 新版宏真实存储不在 settings.db (该库为单向镜像), 外部注入宏不可行

## 七、工具清单

| 文件 | 功能 |
|---|---|
| `定时喊话器.exe` | 定时 `↑+ENTER` 重发喊话 (2-5 分钟随机间隔, 2-3 小时自动停) |
| `mouse_ctl.py` | 全功能控制台: 导出/导入/DPI/绑键/灯效/滚轮/连发/多媒体 |
| `mouse_shout.py` | 侧键触发喊话 (绑键+监听+打字) |
| `mouse_timer.py` | 定时喊话器源码 |
| `mouse_listen_hook.py` | 全通道监听器 (LL Hook + hidapi) |
| `mouse_hid_dump.py` | HID 报告描述符导出+解码 |
| `mouse_mode_export.json` | 鼠标状态导出示例 |
| `mouse_probe_readback.py` 等 | 分析过程脚本 |

## 八、参考

- Kenny-Hui/Instant-A704F-Mouse-Utilities (MIT) — A704 基础协议
- OpenRGB InstantMouseController (GPL-2.0) — RGB 命令
- 本仓库额外贡献: 状态读回缓冲解码 (byte7=灯效模式, byte8=2×活动DPI档)、
  0xF9 扩展键事件、9键喊话鼠标固件连招完整还原
