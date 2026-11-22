---
name: fischertechnik-ft
description: 编辑、生成、配置并校验慧鱼（fischertechnik）ROBO Pro Coding 工程文件 .ft/.ftpy。当用户要往 .ft 里写入程序、改项目配置（名称/模式/控制器 TXT4、RX、BT）、配置电机与传感器引脚、把 Python 塞进图形化工程、批量替换块或代码、检查工程是否可打开时使用。
version: 1.0.0
---

# 慧鱼 ROBO Pro Coding 工程 (.ft) 操控

## 0. 一句话结论

`.ft` **就是 ZIP**，里面全是纯文本：`JSON 元数据 + Blockly XML + Python`。可以直接读、改、重新打包，不需要打开软件。

```
.project.json           {"uuid","name","mode","version","controller","unsaved"}
lib/                    目录条目
lib/controller.blockly  <block type="txt4_controller"> 硬件接口声明
lib/controller.py       由 controller.blockly 生成的 Python
/<项目名>.blockly        主程序（Blockly XML：start_block + 语句）
/<项目名>.py            主程序 Python（图形化模式下是生成物，纯 Python 模式下是源文件）
```

主文件条目名**带前导 `/`**（官方写法），`lib/` 下不带。行尾统一 **LF**。细节见 `references/ft-format.md`。

## 1. 工具

脚本在 `scripts/`，用宿主自带 Python 执行（示例路径）：

```bash
PY="C:\Users\MINT\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
FT="C:\Users\MINT\.claude\skills\fischertechnik-ft\scripts\ft.py"
```

| 命令 | 作用 |
|---|---|
| `ft.py info FILE` | 结构 + 元数据 + 每个条目的块/代码统计 |
| `ft.py ls FILE` | 只列条目 |
| `ft.py extract FILE OUTDIR` | 解压（自动去掉前导 `/`） |
| `ft.py pack INDIR OUT [--name N] [--mode M] [--controller C]` | 从目录打包，自动校验 |
| `ft.py new OUT --name N [--template blocks\|python] [--mode M] [--controller C]` | 生成脚手架工程 |
| `ft.py config FILE [--name N] [--mode M] [--controller C] [--uuid U] [--unsaved 0\|1]` | 改元数据（改名会同步主文件名） |
| `ft.py get FILE /Main.py [--out f]` | 读单个条目 |
| `ft.py put FILE /Main.py src.py` | 替换/新增单个条目 |
| `ft.py verify FILE… [--strict]` | 校验：zip/JSON/XML/Python 语法/块清单/主程序存在性 |
| `scripts/dump_catalog.py` | 从已安装 app.asar 重新提取官方块清单（软件升级后跑一次） |

**默认流程**：`info` → `extract` → 改文件 → `pack` → `verify`。也可以用 `get/put` 做单文件改。

## 2. 两条落地路线（先选一条）

| 场景 | 做法 | 说明 |
|---|---|---|
| A. 用户是图形化工程（`.project.json` 里 `mode:"ADVANCED"`），只想塞代码 | 主程序里放 `util_python` 块，把 Python 写进它的 `<field name="value">` | 官方"Python 代码"块，代码逐字输出；`start_block → util_python(初始化) → loop_endless → util_python(动作)` |
| B. 用户要写真正的 Python 工程 | `config --mode PROFESSIONAL`，主文件 `/<名字>.py` 就是源码 | 该模式下 `isBlocklyMode()===false`，.py 是权威文件，块编辑器不参与 |

**不要**在 ADVANCED 工程里手写 `.py` 当源码：图形化模式会更�� `/<名字>.py`，内容以 `.blockly` 为准。
要长期维护的代码 → 选 B；要"在原有块工程里加逻辑" → 选 A。

## 3. 硬件配置（引脚 / 电机名）

代码侧最稳的写法（等价于把 Motor-0 命名为 M1），不依赖 GUI 连线状态：

```python
M1 = txt_factory.motor_factory.create_motor(TXT_M, 0)   # 0 = Motor-0，1 = Motor-1
```

`TXT_M` 来自 `lib/controller.py`，而 `controller.py` 是 `controller.blockly` 的生成物，规则：

```python
TXT_M = txt_factory.controller_factory.create_graphical_controller()
TXT_M_<引脚名>_<硬件类型> = txt_factory.<引脚类型>_factory.create_<硬件类型>(TXT_M, <引脚序号>)
# 例：TXT_M_M1_motor = txt_factory.motor_factory.create_motor(TXT_M, 0)
```

- 引脚分类：`Input / Output / Motor / Servomotor / Counter / I2C / USB`
- 特例：`reed_switch` 走 `mini_switch` 工厂；`Counter` 引脚上 `encodermotor` → `encodermotor_counter`，其它硬件 → `<硬件>_counter`
- RX 控制器生成的实例名要写成 `controller.<实例>` 前缀

**改 `lib/controller.py` 的注意点**：它会被 `controller.blockly` 重新生成。想永久生效，要么同时在 GUI 里连线（推荐让用户点两下），要么把实例创建写到主程序里（本节第一行那种写法）。

要直接改 `controller.blockly`（不推荐无 GUI 验证就动手）：结构是
`<mutation><arg type="Motor" name="Motor-0" value="M1"/></mutation>` + `<field name="Motor-0">M1</field>` + `<value name="Motor-0"><block type="motor" .../></value>`；
`value` 里必须放**官方硬件实例块**（类型来自 `references/block-catalog.json` 的 `hardware_types`），块 id 要与电机块的 `instance_name` 值 `"<控制器块id>-<引脚块id>"` 对齐。拿不准就走代码路线。

## 4. Python API（从官方代码生成器提取）

| 功能 | 生成代码 |
|---|---|
| 工程头 | `from lib.controller import *` |
| 电机 | `from fischertechnik.controller.Motor import Motor`；`.set_speed(int(100), Motor.CW)` / `Motor.CCW`；`.start()`；`.stop()`；`.get_speed()`；`.is_running()` |
| 多电机同步 | 每个 `.set_speed(...)` 之后 `.start_sync(a, b)` |
| 编码电机 | `.set_speed(int(v), dir)`、`.set_distance(int(d), ...)`、`.stop()` |
| 舵机 | `.set_position(...)` / `.get_position()` |
| 等待 | `time.sleep(秒)`；毫秒块生成 `time.sleep(ms / 1000)` |
| 自定义代码 | `util_python` 块 → 字段 `value` 原文输出 |

完整块类型 / 硬件类型 / 字段名清单：`references/block-catalog.json`（213 块、26 硬件、56 字段，从 app.asar 自动提取）。

## 5. 坑（踩过的）

1. **语句输入名按块而定，写错子块会被静默丢弃**：`start_block` 是 `statement`，`loop_endless` 是 **`DO`**（官方 `appendStatementInput("DO")` + `statementToCode(c,"DO")`）。写成 `statement` 时软件里循环体是空的、代码块消失。完整映射见 `references/block-catalog.json` 的 `block_statement_inputs`，`ft.py verify` 会硬拦。
2. 条目名带前导 `/`；`ft.py` 查找时会归一化，自己手写 zip 时别忘。
3. 元数据 `unsaved:true` 会让软件认为有未保存改动；生成文件请置 `false`。
4. `mode` 只有 `ADVANCED`（图形化）/ `PROFESSIONAL`（纯 Python）/ `UNDEFINED`。
5. 主文件名必须与 `name` 一致，否则加载后可能被改名或识别不到主程序（`ft.py config --name` 已自动同步）。
6. **不要臆造块类型**：未知类型在 Blockly 里会被丢弃甚至报错。只用 `references/block-catalog.json` 里的类型；`verify --strict` 会拦。
7. 块内字段名区分大小写，且带索引后缀：`instance_name_0`、`direction_0`；等待块的数值输入名是 `value`，格式字段 `format`（`s` / `ms`）。
8. XML 头保留 `<xml xmlns="https://developers.google.com/blockly/xml" version="23">`。
9. `.py` 只是缓存时，缩进用 2 空格（官方生成风格），LF 行尾。
10. 部分块（电机/同步）带 mutator，缺 `<mutation>` 时按单电机形态渲染——够用，别硬造 mutation。
11. 改完工程后如果软件里已经打开旧版本，需要关闭工程/重新打开才会读到新文件。
12. `app.asar` 里没有示例工程；需要真实样例就从用户已有 `.ft` 里取模板。

## 5.1 改完必须自测

```bash
"$PY" scripts/selftest.py     # 负例必须被拦、正例必须通过、现有工程必须全绿
```

## 6. 交付前自检

```bash
"$PY" "$FT" verify "工程.ft"
```

必须全绿：`.project.json` 可解析且字段齐全、`mode/controller` 合法、主程序条目存在、XML 可解析、`.py` 通过 `py_compile`。改名前后的工程各跑一次；原文件不要覆盖，产出新文件或先备份。
