"""Blockly XML building blocks, verified against the real ROBO Pro Coding app.

Everything here mirrors what the application itself writes, in particular:

* ``start_block``      statement input name  ``statement``
* ``loop_endless``     statement input name  ``DO``        (NOT ``statement``)
* motor block          fields ``instance_name_<n>`` / ``direction_<n>``,
                       value ``<controller-id>-<pin-block-id>``
* controller block     one ``<arg>``/``<field>``/``<value>`` per pin

Getting the statement input name wrong makes Blockly *silently drop* the
children, which is why :mod:`ftgateway.verify` checks it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .project import Project

XML_HEAD = '<xml xmlns="https://developers.google.com/blockly/xml" version="23">'
PIN_ORDER = ("Input", "Output", "Motor", "Servomotor", "Counter", "I2C", "USB")
PIN_CLASS = {
    "Input": "Input",
    "Output": "Output",
    "Motor": "Motor",
    "Servomotor": "Servomotor",
    "Counter": "Counter",
    "I2C": "I2C",
    "USB": "USB",
}
# hardware block type attached inside a pin (see data/block-catalog.json)
PIN_HARDWARE = {
    "Input": "mini_switch",
    "Output": "led",
    "Motor": "motor",
    "Servomotor": "servomotor",
    "Counter": "motor_step_counter",
    "I2C": "combined_sensor",
    "USB": "camera",
}
# factory call emitted into lib/controller.py
PIN_FACTORY = {
    "Input": "mini_switch",
    "Output": "led",
    "Motor": "motor",
    "Servomotor": "servomotor",
    "Counter": "motor_step_counter",
    "I2C": "combined_sensor",
    "USB": "camera",
}

CONTROLLER_PY_TEMPLATE = """import fischertechnik.factories as txt_factory
from fischertechnik.control.RemoteControl import RemoteControl
from fischertechnik.control.VoiceControl import VoiceControl

voice_control = None
remote_control = None


def get_voice_control():
  global voice_control
  if voice_control is None:
    voice_control = VoiceControl()
  return voice_control


def get_remote_control():
  global remote_control
  if remote_control is None:
    remote_control = RemoteControl()
  return remote_control


txt_factory.init()


TXT_M = txt_factory.controller_factory.create_graphical_controller()
{instances}
txt_factory.initialized()
"""


def _indent(text: str, spaces: int = 2) -> str:
    pad = " " * spaces
    return "\n".join(pad + line if line.strip() else line for line in text.splitlines())


# --------------------------------------------------------------------- blocks
def controller_blockly(controller_id: str, pins: Dict[str, List[Tuple[str, str]]]) -> str:
    """Build ``lib/controller.blockly``.

    ``pins`` maps a pin class to ``[(instance name, pin block id), ...]``,
    e.g. ``{"Motor": [("M1", "pinMotor00000001")]}``.
    """
    args: List[str] = []
    fields: List[str] = []
    values: List[str] = []

    for pin_class in PIN_ORDER:
        entries = pins.get(pin_class) or []
        if not entries:
            args.append(f'      <arg type="{pin_class}" name="{pin_class}-0" value="-"/>')
            fields.append(f'    <field name="{pin_class}-0">-</field>')
            continue
        for index, (instance, pin_id) in enumerate(entries):
            name = f"{pin_class}-{index}"
            args.append(f'      <arg type="{pin_class}" name="{name}" value="{instance}"/>')
            fields.append(f'    <field name="{name}">{instance}</field>')
            hardware = PIN_HARDWARE[pin_class]
            values.append(
                f'    <value name="{name}">\n'
                f'      <block type="{hardware}" id="{pin_id}"/>\n'
                f"    </value>"
            )

    body = "\n".join(
        [
            XML_HEAD,
            f'  <block type="txt4_controller" id="{controller_id}" x="0" y="0">',
            "    <mutation>",
            *args,
            "    </mutation>",
            '    <field name="mode">0</field>',
            '    <field name="controller_name">TXT</field>',
            *fields,
            *values,
            "  </block>",
            "</xml>",
        ]
    )
    return body + "\n"


def controller_python(pins: Dict[str, List[Tuple[str, str]]]) -> str:
    """Build ``lib/controller.py`` (what the app generates for the pins)."""
    lines: List[str] = []
    for pin_class, entries in pins.items():
        for index, (instance, _pin_id) in enumerate(entries):
            factory = PIN_FACTORY[pin_class]
            lines.append(
                f"TXT_M_{instance}_{factory} = "
                f"txt_factory.{pin_class.lower()}_factory.create_{factory}(TXT_M, {index})"
            )
    return CONTROLLER_PY_TEMPLATE.format(instances="\n".join(lines) if lines else "")


def start_block(body: str = "", block_id: str = "startBlock0000001") -> str:
    inner = body or ""
    return (
        f'  <block type="start_block" id="{block_id}" deletable="false" x="-460" y="-180">\n'
        f'    <statement name="statement">\n{inner}\n    </statement>\n'
        f"  </block>"
    )


def loop_endless(body: str = "", block_id: str = "loopEndless000001") -> str:
    """Infinite loop. The statement input is named ``DO`` — not ``statement``."""
    inner = body or ""
    return (
        f'  <block type="loop_endless" id="{block_id}">\n'
        f'    <statement name="DO">\n{inner}\n    </statement>\n'
        f"  </block>"
    )


def util_python(code: str, block_id: str = "pythonBlock00000001") -> str:
    """The official "Python 代码" block — emits the text verbatim."""
    return (
        f'      <block type="util_python" id="{block_id}">\n'
        f'        <field name="value">{_escape(code)}</field>\n'
        f"      </block>"
    )


def math_number(value: float | int, block_id: str = "mathNumber00000001") -> str:
    return (
        f'      <shadow type="math_number" id="{block_id}">'
        f'<field name="NUM">{value}</field></shadow>'
    )


def motor_set_speed(
    controller_id: str,
    pin_id: str,
    speed: int | float = 512,
    direction: str = "Motor.CW",
    block_id: str = "motorSpeed0000001",
) -> str:
    return (
        f'      <block type="motor_set_speed" id="{block_id}">\n'
        f'        <field name="instance_name_0">{controller_id}-{pin_id}</field>\n'
        f'        <field name="direction_0">{direction}</field>\n'
        f'        <value name="speed">{math_number(speed)}</value>\n'
        f"      </block>"
    )


def motor_stop(
    controller_id: str, pin_id: str, block_id: str = "motorStop000000001"
) -> str:
    return (
        f'      <block type="motor_stop" id="{block_id}">\n'
        f'        <field name="instance_name_0">{controller_id}-{pin_id}</field>\n'
        f"      </block>"
    )


def wait_for(seconds: float = 1, block_id: str = "waitBlock00000001") -> str:
    return (
        f'      <block type="util_wait_for" id="{block_id}">\n'
        f'        <field name="format">s</field>\n'
        f'        <value name="value">{math_number(seconds)}</value>\n'
        f"      </block>"
    )


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def block_of(block_xml: str) -> str:  # helper kept for readability
    return block_xml


# -------------------------------------------------------------------- builder
class ProjectBuilder:
    """Assemble a graphical (ADVANCED) project with pins and a block program."""

    def __init__(
        self,
        name: str,
        controller_id: str = "ctrl000000000001",
        pin_id: str = "pinMotor00000001",
        controller: str = "TXT4",
    ):
        self.name = name
        self.controller_id = controller_id
        self.pin_id = pin_id
        self.controller = controller
        self.pins: Dict[str, List[Tuple[str, str]]] = {}
        self._main_blocks: List[str] = []
        self._counter = 0

    # -- pins ---------------------------------------------------------------
    def add_motor(self, instance: str = "M1", pin_id: Optional[str] = None) -> str:
        pin_id = pin_id or self.pin_id
        self.pins.setdefault("Motor", []).append((instance, pin_id))
        return pin_id

    def add_input(self, instance: str = "I1", pin_id: str = "pinInput00000001") -> str:
        self.pins.setdefault("Input", []).append((instance, pin_id))
        return pin_id

    def add_output(self, instance: str = "O1", pin_id: str = "pinOutput00000001") -> str:
        self.pins.setdefault("Output", []).append((instance, pin_id))
        return pin_id

    # -- program ------------------------------------------------------------
    def add(self, xml: str) -> None:
        self._main_blocks.append(xml)

    def motor(self, instance: str = "M1", speed: int = 512, direction: str = "Motor.CW") -> None:
        pin_id = self._pin_id_for("Motor", instance)
        self.add(motor_set_speed(self.controller_id, pin_id, speed, direction))

    def motor_off(self, instance: str = "M1") -> None:
        pin_id = self._pin_id_for("Motor", instance)
        self.add(motor_stop(self.controller_id, pin_id))

    def wait(self, seconds: float = 1) -> None:
        self.add(wait_for(seconds))

    def _pin_id_for(self, pin_class: str, instance: str) -> str:
        for name, pin_id in self.pins.get(pin_class, []):
            if name == instance:
                return pin_id
        if pin_class == "Motor":
            return self.add_motor(instance)
        raise ValueError(f"no {pin_class} pin named {instance}")

    # -- output -------------------------------------------------------------
    def main_blockly(self, loop: bool = True) -> str:
        body = "\n".join(self._main_blocks)
        inner = loop_endless(body) if loop else body
        return f"{XML_HEAD}\n{start_block(inner)}\n</xml>\n"

    def controller_blockly(self) -> str:
        return controller_blockly(self.controller_id, self.pins)

    def controller_python(self) -> str:
        return controller_python(self.pins)

    def build(self) -> Project:
        project = Project.create(self.name, "ADVANCED", self.controller)
        project.put("lib/controller.blockly", self.controller_blockly())
        project.put("lib/controller.py", self.controller_python())
        project.put(f"/{self.name}.blockly", self.main_blockly())
        project.put(f"/{self.name}.py", self.main_python())
        return project

    def main_python(self) -> str:
        """Python mirror of the block program (the app regenerates it)."""
        lines = ["from lib.controller import *", "", "import time",
                 "from fischertechnik.controller.Motor import Motor", "", "while True:"]
        body: List[str] = []
        for xml in self._main_blocks:
            body.extend(_python_for_block(xml))
        lines.extend(["  " + line if line else line for line in body] or ["  pass"])
        return "\n".join(lines) + "\n"


def _python_for_block(xml: str) -> List[str]:
    """Translate the small subset of blocks produced by :class:`ProjectBuilder`."""
    lines: List[str] = []
    if 'type="motor_set_speed"' in xml:
        speed = _field(xml, "NUM", default="512")
        direction = _field(xml, "direction_0", default="Motor.CW")
        lines += [
            f"TXT_M_M1_motor.set_speed(int({speed}), {direction})",
            "TXT_M_M1_motor.start()",
        ]
    elif 'type="motor_stop"' in xml:
        lines.append("TXT_M_M1_motor.stop()")
    elif 'type="util_wait_for"' in xml:
        lines.append(f"time.sleep({_field(xml, 'NUM', default='1')})")
    return lines


def _field(xml: str, name: str, default: str = "") -> str:
    marker = f'name="{name}"'
    index = xml.find(marker)
    if index < 0:
        return default
    start = xml.find(">", index) + 1
    end = xml.find("<", start)
    return xml[start:end] if end > start else default


# ------------------------------------------------------------------ recipes
def build_motor_run(
    name: str = "Motor_Run",
    speed: int = 512,
    direction: str = "Motor.CW",
    hold: float = 0.1,
) -> Project:
    """M1 keeps turning forever (black motor on Motor-0)."""
    builder = ProjectBuilder(name)
    builder.add_motor("M1")
    builder.motor("M1", speed, direction)
    builder.wait(hold)
    return builder.build()


def build_led_blink(name: str = "LED_Blink", speed: int = 512, hold: float = 1) -> Project:
    """LED on M1 blinks: H-bridge reverses the direction every ``hold`` seconds."""
    builder = ProjectBuilder(name)
    builder.add_motor("M1")
    builder.motor("M1", speed, "Motor.CW")
    builder.wait(hold)
    builder.motor("M1", speed, "Motor.CCW")
    builder.wait(hold)
    return builder.build()


def build_led_steady(name: str = "LED_On", speed: int = 512) -> Project:
    """LED on M1 stays lit (constant forward drive)."""
    builder = ProjectBuilder(name)
    builder.add_motor("M1")
    builder.motor("M1", speed, "Motor.CW")
    builder.wait(0.1)
    return builder.build()


def build_python_project(name: str = "PyProgram", source: Optional[str] = None) -> Project:
    """Python-only project (``mode=PROFESSIONAL``)."""
    project = Project.create(name, mode="PROFESSIONAL", controller="TXT4")
    project.put("lib/controller.py", controller_python({"Motor": [("M1", "pinMotor00000001")]}))
    code = source or (
        "from lib.controller import *\n"
        "from fischertechnik.controller.Motor import Motor\n"
        "import time\n\n\n"
        "M1 = txt_factory.motor_factory.create_motor(TXT_M, 0)\n\n"
        "while True:\n"
        "  M1.set_speed(int(512), Motor.CW)\n"
        "  M1.start()\n"
        "  time.sleep(0.1)\n"
    )
    project.put(f"/{name}.py", code)
    return project
