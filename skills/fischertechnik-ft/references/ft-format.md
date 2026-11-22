# .ft 格式与生成规则（实测记录）

观测来源：解包用户工程 `Untitled.ft`；反解已安装 `ROBO Pro Coding` 的 `app.asar`
（`client/www/main.<hash>.js`，webpack 打包）中的常量与代码生成器。

## 1. 容器

`.ft` = ZIP（deflate 或 store 均可）。实测原件 2618 字节，条目：

| 条目 | 大小 | 说明 |
|---|---|---|
| `.project.json` | 134 | 元数据，第一个条目 |
| `lib/` | 0 | 目录条目（有 external_attr 目录位） |
| `lib/controller.blockly` | 888 | 控制器块 |
| `lib/controller.py` | 611 | 控制器 Python |
| `/Untitled.blockly` | 288 | 主程序块 |
| `/Untitled.py` | 49 | 主程序 Python |

要点：
- 主文件条目名**带前导 `/`**；`lib/` 下的不带。
- 全部文件 **LF** 行尾，UTF-8 无 BOM。
- `.py` 缩进 2 空格（官方生成风格）。

官方常量（来自 bundle）：

```js
ZIP_EXTENSION="ft"; LIB_DIRECTORY="lib"; DATA_DIRECTORY="data";
PROJECT_CONFIG_FILENAME=".project.json"; CONTROLLER_FILENAME="lib/controller.py";
SOURCECODE_FILENAME="lib/<basename>.py"; MAIN_FILENAME="main.py";
CAMERA_FILENAME="lib/camera.xml"; DISPLAY_FILENAME="lib/display.xml";
REMOTE_CONTROL_FILENAME="lib/control.xml"; NEURAL_NETWORK_FILENAME="lib/neural_network.json";
```

工程类型：`.ft`（块）、`.sb3`（Scratch）、`.ftpy`（Python 工程）、`.py`。
判定：zip 内条目数 >1 且存在 `.project.json` → 按 `.ft` 打开。

## 2. `.project.json`

```json
{"uuid":"57712aaa-ed64-49b3-8cb4-ecedad6c63c8","name":"Untitled","mode":"ADVANCED","version":"1.0","controller":"TXT4","unsaved":true}
```

| 字段 | 取值 |
|---|---|
| `uuid` | 工程唯一 id（新工程用 uuid4） |
| `name` | 工程名，必须与主文件名一致 |
| `mode` | `ADVANCED`（图形化）/ `PROFESSIONAL`（纯 Python）/ `UNDEFINED` |
| `version` | 固定 `"1.0"` |
| `controller` | `TXT4` / `RX` / `BT_SMART` |
| `unsaved` | 生成的文件置 `false` |

模式判定（bundle）：

```js
isBlocklyMode(){ return !!this.project && this.project.mode !== "PROFESSIONAL" }
```

## 3. `lib/controller.blockly`

空工程形态（原件）：

```xml
<xml xmlns="https://developers.google.com/blockly/xml" version="23">
  <block type="txt4_controller" id="..." x="0" y="0">
    <mutation>
      <arg type="Input" name="Input-0" value="-"/>
      <arg type="Output" name="Output-0" value="-"/>
      <arg type="Motor" name="Motor-0" value="-"/>
      <arg type="Servomotor" name="Servomotor-0" value="-"/>
      <arg type="Counter" name="Counter-0" value="-"/>
      <arg type="I2C" name="I2C-0" value="-"/>
      <arg type="USB" name="USB-0" value="-"/>
    </mutation>
    <field name="mode">0</field>
    <field name="controller_name">TXT</field>
    <field name="Input-0">-</field>
    ...
  </block>
</xml>
```

- `field name="mode"`：`0` = 主控制器，其它数字 = 扩展控制器（`EXT_<n>`）。
- `field name="controller_name"`：显示名，第三方生成实例名时用 `<name>_<引脚名>_<类型>`。
- 引脚字段名固定为 `<分类>-<序号>`，占位值 `"-"` 表示未接。
- 接了硬件后：`value` 名 = `<分类>-<序号>`，里面放官方硬件实例块（`motor` / `mini_switch` / `ultrasonic_distance_meter` …，
  见 `block-catalog.json` 的 `hardware_types`），同时 `mutation` 的 `arg value` 与同名 `field` 文本改成实例名（`M1`、`I1`…）。
- 电机块里的 `instance_name` 值格式为 `"<控制器块id>-<引脚块id>"`；匹配不到时生成器把该值**直接当实例名**用。

## 4. `lib/controller.py` 生成规则

生成器伪码（bundle `yJ.prototype.toPythonCode`）：

```
<name> = txt_factory.controller_factory.create_graphical_controller(<index 或空>)
for pin in pins:
    <name>_<field值>_<type小写> = txt_factory.<pin类型小写>_factory.create_<type小写>(<name>, <pin序号>)
```

特例：
- `reed_switch` → `create_mini_switch(...)`
- `Counter` 引脚：`encodermotor` → `encodermotor_counter`；其它 → `<type>_counter`
- RX 控制器：实例名前面加 `controller.`
- 主控制器额外写出 `voice_control` / `remote_control` 的 import 与 `None` 初始化（见原件）

原件（TXT4、无接线）就是：

```python
import fischertechnik.factories as txt_factory
from fischertechnik.control.RemoteControl import RemoteControl
from fischertechnik.control.VoiceControl import VoiceControl
...
txt_factory.init()
TXT_M = txt_factory.controller_factory.create_graphical_controller()
txt_factory.initialized()
```

## 5. 主程序 `/<name>.blockly`

```xml
<xml xmlns="https://developers.google.com/blockly/xml" version="23">
  <block type="start_block" id="..." deletable="false" x="-463" y="-189">
    <statement name="statement">
      <block type="loop_endless" id="..."/>
    </statement>
  </block>
</xml>
```

- 顶层只有 `start_block`；语句挂 `<statement name="statement">`，顺序执行用 `<next>` 串接。
- `loop_endless` 的语句输入名是 **`DO`**（不是 `statement`）：
  `jsonInit({message0:..., message1:"%{BKY_CONTROLS_REPEAT_INPUT_DO} %1", args1:[{type:"input_statement",name:"DO"}]})`，
  生成器 `statementToCode(c,"DO")` → `while True:`。**写错名字时里面的块会被静默丢弃**（软件里显示空循环）。
- 其它块的语句输入名从 `block-catalog.json` 的 `block_statement_inputs` 查（27 个块有映射），
  `ft.py verify` 会按块类型校验，写错直接 FAIL。
- 空工程的 `/<name>.py` 是 `from lib.controller import *\n\nwhile True:\n  pass\n`。

## 6. `util_python`（"Python 代码"块）

定义（bundle）：单 dummy input + 字段 `value`（多行文本域），语句块。

```xml
<block type="util_python" id="...">
  <field name="value">print("hi")
time.sleep(1)</field>
</block>
```

生成代码 = 字段内容 + `"\n"`，由生成器负责缩进。TXT4/RX（无遥控文件）都可用，只有 BT_SMART 被禁用。

## 7. Python API（生成器原文）

| 块 | 生成代码 |
|---|---|
| `motor_set_speed` | `<inst>.set_speed(int(<speed>), <direction>)\n` + `<inst>.start()\n`；多电机时 `.start_sync(a, b)` |
| `motor_stop` | `<inst>.stop()` |
| `motor_get_speed` | `<inst>.get_speed()` |
| `motor_if_running` | `<inst>.is_running()` |
| `encodermotor_set_values` | `.set_speed(int(v), dir)` + `.set_distance(int(d), ...)` |
| `servomotor_*` | `.set_position(...)` / `.get_position()` |
| `util_wait_for` | `time.sleep(<秒>)`；`format=="ms"` 时 `time.sleep(<ms> / 1000)` |
| 电机方向 | 字段值就是字面量 `Motor.CW` / `Motor.CCW`，需要 `from fischertechnik.controller.Motor import Motor` |

## 8. 刷新证据

```bash
python scripts/dump_catalog.py           # 自动探测已安装 app.asar
python scripts/dump_catalog.py --asar "C:\...\app\resources\app.asar"
```

输出 `references/block-catalog.json`：`block_types` / `hardware_types` / `field_names` / 各枚举原映射。
`ft.py verify --strict` 用它拦截臆造块类型。

`app.asar` 解析要点（脚本内已实现）：8 字节头（`uint32 4` + `uint32 pickle_size`）→ pickle 里第一个 `{` 到最后一个 `}` 是 JSON 目录 →
文件数据从 `8 + pickle_size` 起，按条目 `offset/size` 读取。bundle 路径形如 `client/www/main.<hash>.js`。
