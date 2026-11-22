# ROBO Pro Coding Run API Gateway

[![tests](https://img.shields.io/badge/tests-13%20passed-brightgreen)](tests/)
[![python](https://img.shields.io/badge/python-3.9%2B-blue)](pyproject.toml)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**目标版本：ROBO Pro Coding 6.5.4**（Electron 31.7.7, TXT 4.0）。块标识与生成代码是该版本的快照，
软件升级后用 `bridge/dumpblocks.js` 重新导出。

用 Python 生成、校验、驱动**慧鱼 ROBO Pro Coding** 工程（`.ft`）。
`.ft` 就是 JSON + Blockly XML + Python 的 ZIP——所以机器人程序可以像源码一样生成、比对、测试。

```bash
pip install -e .
ftg gen motor-run --name Motor_Run --speed 512    # M1 上的电机一直转
ftg verify Motor_Run.ft --strict                  # 容器、XML、块名、语法
```

## 命令

| 命令 | 用途 |
|---|---|
| `ftg gen motor-run\|led-blink\|led-on\|python` | 生成可直接打开的工程 |
| `ftg verify FILE --strict` | 离线校验（见下） |
| `ftg info` · `ftg ls` | 结构与元数据 |
| `ftg extract` · `pack` · `get` · `put` · `config` | 条目级编辑 |
| `ftg blocks 电机` | 搜 314 个块的字典 |

零第三方依赖，Python 3.9+。

## API

```python
from ftgateway import build_motor_run, verify
from ftgateway.blocks import ProjectBuilder

build_motor_run("Motor_Run", speed=512).save("Motor_Run.ft")
print(verify("Motor_Run.ft", strict=True))

b = ProjectBuilder("Conveyor")
b.add_motor("M1")
b.motor("M1", speed=300)
b.wait(2)
b.motor_off("M1")
b.build().save("Conveyor.ft")
```

## 交给智能体

克隆后对它说一句：

> 读 `AGENTS.md`，用 `ftg` 生成并校验我的 `.ft` 工程。

`AGENTS.md` 里有格式、命令、两个静默失败规则和校验流程；`src/ftgateway/data/` 的 314 块字典是事实来源。
可选 skill：`./skills/install-skill.sh`（或 `.ps1`）。

## 桥接（可选，Windows）

通过 DevTools 协议驱动已安装的应用：打开工程、读实时工作区、让软件自己生成 Python。

```powershell
.\bridge\launch.ps1 -Port 9334          # 清 ELECTRON_RUN_AS_NODE，独立 profile
node bridge\setfile.js out.ft           # 注入文件，不弹对话框
node bridge\verify_in_app.js ctrl.blockly main.blockly
node bridge\cdp.js shot proof.png
```

## 它拦掉的两个静默失败

| 坑 | 现象 | 规则 |
|---|---|---|
| 语句输入名写错 | 循环体空，无报错 | `loop_endless` 用 `DO`；`start_block` 用 `statement` |
| 引脚实例名不匹配 | 代码变成 `-.set_speed(...)` | `instance_name_0` = `<控制器id>-<引脚块id>` |

两条都固化在 `src/ftgateway/blocks.py`，由 `ftg verify` 强制。

## 验证到哪一步

| 层次 | 证据 |
|---|---|
| 容器/元数据 | 单元测试、extract→pack 往返（应用 6.5.4） |
| 块 XML | 运行中的应用内，用它自己的 Blockly 解析 |
| 生成的 Python | 由应用的 `pythonGenerator` 现场产出 |
| 实机 | TXT 4.0：M1 电机转、M1 上的 LED 闪 |

## 结构

```
src/ftgateway/      库 + CLI            bridge/     DevTools 桥
src/ftgateway/data/ 块字典 + 完整 schema  docs/       格式、桥接、块、排障
examples/           3 个可打开工程       tests/      13 个单元测试
```

## 法律

非官方第三方工具，与 fischertechnik GmbH、beemo GmbH 无隶属或背书关系。代码与文档为 MIT；
`data/*.json` 是从本机已装应用导出的互操作性元数据，界面文案与生成片段的权利归其所有人，
**不在** MIT 授权范围内（见 [NOTICE.md](NOTICE.md)）。不含软件本体、固件、素材或语言包。
使用桥接前请备份 `.ft`。

## 路线图

`ftg upload`（直接下发到控制器）· Python AST → 块 · 传感器配方。
