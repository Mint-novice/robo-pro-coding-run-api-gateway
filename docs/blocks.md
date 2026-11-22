# Block reference

`src/ftgateway/data/block-schema.json` is a dump of the application's own Blockly
registry: **314 blocks**, each with

* `type` — the XML `type` attribute
* `title` — the UI title (Chinese in a zh install)
* `inputs` — statement/value inputs with their names and type checks
* `fields` — field names, field classes and default values
* `code` — the Python the block emits (`<highlight>` markers stripped)

Regenerate with `bridge/dumpblocks.js`. Search it from the CLI:

```bash
ftg blocks motor
ftg blocks 超声波
```

## Frequent blocks

| type | title (zh) | key inputs | key fields | emits |
|---|---|---|---|---|
| `start_block` | 程序开始 | `statement` | – | program entry |
| `loop_endless` | 无限重复 | **`DO`** | – | `while True:` |
| `controls_repeat_ext` | 重复 | `TIMES`, `DO` | – | `for count in range(n):` |
| `util_wait_for` | 等待 | `value` | `format` (`s`/`ms`) | `time.sleep(...)` |
| `util_python` | Python 代码 | – | `value` | verbatim text |
| `motor_set_speed` | 设置电机 | `speed` | `instance_name_0`, `direction_0` | `.set_speed(int(v), Motor.CW)` + `.start()` |
| `motor_stop` | 停止电机 | – | `instance_name_0` | `.stop()` |
| `motor_get_speed` | 获取电机速度 | – | `instance_name` | `.get_speed()` |
| `encodermotor_set_values` | 编码电机 定位 | `speed`, `distance` | `instance_name_0`, `direction_0` | `.set_speed(...)` + `.set_distance(...)` |
| `servomotor_set_position` | 舵机 位置 | `position` | `instance_name` | `.set_position(...)` |
| `output_led_set_value` | 设置 LED 亮度 | `value` | `instance_name` | `.set_brightness(int(v))` |
| `unidirectional_motor_set_speed` | 输出端电机速度 | `value` | `instance_name` | `.set_speed(int(v))` |
| `input_mini_switch_get_state` | 获取微型开关 | – | `instance_name` | `.get_state()` |
| `input_ultrasonic_sensor_get_value` | 获取超声波距离 | – | `instance_name` | `.get_distance()` |
| `input_color_sensor_get_value` | 获取颜色数值 | – | `instance_name` | `.get_value()` |
| `txt4_controller` | 控制器 | pin `value`s | `mode`, `controller_name`, `<pin>-<n>` | `create_graphical_controller()` |
| `motor` | 电机 | – | – | pin hardware block (no code) |

## Writing a block by hand

```xml
<block type="motor_set_speed" id="m1">
  <field name="instance_name_0">ctrl000000000001-pinMotor00000001</field>
  <field name="direction_0">Motor.CW</field>
  <value name="speed">
    <shadow type="math_number"><field name="NUM">512</field></shadow>
  </value>
</block>
```

* `instance_name_*` / `direction_*` are **indexed** for the sync-motor mutator.
* the value input for speed is `speed`; its shadow block is `math_number`.
* a wrong value for `instance_name_*` is silently replaced by `-` by the field
  validator, which produces `-.set_speed(...)` — always copy the id pair from
  `lib/controller.blockly`.

## Layout of the JSON entry

```json
{
  "type": "motor_set_speed",
  "title": "设置电机 - 逆时针 速度 ?",
  "inputs": [{"name": "speed", "type": 1, "check": ["Number"]}],
  "fields": [{"name": "instance_name_0", "cls": "zc", "value": "-"}],
  "code": "-.set_speed(int())\n"
}
```

`inputs[].type` is Blockly's `input_value` / `input_statement` / `input_dummy`
enum (1 / 3 / 5).
