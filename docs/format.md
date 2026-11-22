# `.ft` container format

Observed on **ROBO Pro Coding 6.5.4** (Electron 31.7.7, TXT 4.0). Everything below is verified by
reading files the application itself wrote.

## ZIP layout

| entry | meaning |
|---|---|
| `.project.json` | project metadata (first entry) |
| `lib/` | directory entry |
| `lib/controller.blockly` | controller block, i.e. the pin configuration |
| `lib/controller.py` | Python generated from that block |
| `/<name>.blockly` | main program (Blockly XML) |
| `/<name>.py` | main program Python |

Main-file entries carry a leading `/`; `lib/` entries do not. All files are
UTF-8 with LF line endings, generated `.py` uses 2-space indentation.

## `.project.json`

```json
{"uuid":"…","name":"Motor_Run","mode":"ADVANCED","version":"1.0","controller":"TXT4","unsaved":false}
```

| field | values |
|---|---|
| `mode` | `ADVANCED` (blocks) / `PROFESSIONAL` (Python only) / `UNDEFINED` |
| `controller` | `TXT4` / `RX` / `BT_SMART` |
| `unsaved` | set `false` for generated files |

The app decides with `isBlocklyMode() => mode !== "PROFESSIONAL"`, so a
`PROFESSIONAL` project ignores `.blockly` completely.

## Controller block

```xml
<block type="txt4_controller" id="ctrl000000000001" x="0" y="0">
  <mutation>
    <arg type="Motor" name="Motor-0" value="M1"/>
  </mutation>
  <field name="mode">0</field>
  <field name="controller_name">TXT</field>
  <field name="Motor-0">M1</field>
  <value name="Motor-0">
    <block type="motor" id="pinMotor00000001"/>
  </value>
</block>
```

* `mode` = `0` for the master controller, other numbers for extensions.
* pin fields are named `<class>-<index>`; `-` means “nothing attached”.
* attaching hardware means: `mutation/arg@value` + same-named `<field>` get the
  instance name, and a `<value>` wraps the official hardware block.

## Generated controller Python

```python
TXT_M = txt_factory.controller_factory.create_graphical_controller()
TXT_M_M1_motor = txt_factory.motor_factory.create_motor(TXT_M, 0)
```

Rule: `<controller>_<instance>_<hardware> = txt_factory.<pinclass>_factory.create_<hardware>(<controller>, <pin index>)`.
Special cases in the app: `reed_switch` goes through `mini_switch`, counters use
`<hardware>_counter`, and RX instances are prefixed with `controller.`.

## Main program

```xml
<xml xmlns="https://developers.google.com/blockly/xml" version="23">
  <block type="start_block" id="start" deletable="false" x="-460" y="-180">
    <statement name="statement">
      <block type="loop_endless" id="loop">
        <statement name="DO">
          <block type="motor_set_speed" id="m1">
            <field name="instance_name_0">ctrl000000000001-pinMotor00000001</field>
            <field name="direction_0">Motor.CW</field>
            <value name="speed">
              <shadow type="math_number"><field name="NUM">512</field></shadow>
            </value>
          </block>
        </statement>
      </block>
    </statement>
  </block>
</xml>
```

* `start_block` uses the statement input `statement`.
* `loop_endless` uses `DO` — **any other name silently drops the children**.
* statement chaining inside a body uses `<next>`.
* motor fields are indexed: `instance_name_0`, `direction_0`; the value input is
  `speed` and its default shadow block is `math_number` with field `NUM`.

## Python emitted by the app

```python
from lib.controller import *
import time
from fischertechnik.controller.Motor import Motor

while True:
  TXT_M_M1_motor.set_speed(int(512), Motor.CW)
  TXT_M_M1_motor.start()
  time.sleep(0.1)
```

Useful API surface (all taken from the app's own generators):

| block | Python |
|---|---|
| `motor_set_speed` | `<inst>.set_speed(int(v), Motor.CW|Motor.CCW)` + `<inst>.start()` |
| `motor_stop` | `<inst>.stop()` |
| `motor_get_speed` | `<inst>.get_speed()` |
| `encodermotor_*` | `.set_speed(...)`, `.set_distance(...)` |
| `util_wait_for` | `time.sleep(seconds)` (`format=ms` divides by 1000) |
| `util_python` | the field text, verbatim |
