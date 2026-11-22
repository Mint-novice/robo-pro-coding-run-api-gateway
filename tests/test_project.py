"""Regression tests for the ftgateway toolkit (stdlib unittest, pytest compatible)."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ftgateway import (  # noqa: E402
    Project,
    build_led_blink,
    build_led_steady,
    build_motor_run,
    build_python_project,
    verify,
)
from ftgateway.blocks import controller_blockly, motor_set_speed, wait_for  # noqa: E402

BAD_LOOP = """<xml xmlns="https://developers.google.com/blockly/xml" version="23">
  <block type="start_block" id="S" deletable="false" x="0" y="0">
    <statement name="statement">
      <block type="loop_endless" id="L">
        <statement name="statement">
          <block type="util_python" id="U"><field name="value">x = 1</field></block>
        </statement>
      </block>
    </statement>
  </block>
</xml>
"""

GOOD_LOOP = BAD_LOOP.replace(
    '<statement name="statement">\n          <block type="util_python"',
    '<statement name="DO">\n          <block type="util_python"',
)


class ProjectTests(unittest.TestCase):
    def test_container_layout(self) -> None:
        project = build_motor_run("Motor_Run")
        names = project.entries()
        self.assertEqual(names[0], ".project.json")
        self.assertIn("lib/", names)
        self.assertIn("lib/controller.blockly", names)
        self.assertIn("/Motor_Run.blockly", names)
        self.assertIn("/Motor_Run.py", names)

    def test_metadata(self) -> None:
        project = build_motor_run("Motor_Run")
        cfg = project.config
        self.assertEqual(cfg["name"], "Motor_Run")
        self.assertEqual(cfg["mode"], "ADVANCED")
        self.assertEqual(cfg["controller"], "TXT4")
        self.assertFalse(cfg["unsaved"])

    def test_recipes_pass_verification(self) -> None:
        for factory in (build_motor_run, build_led_blink, build_led_steady, build_python_project):
            with self.subTest(recipe=factory.__name__):
                result = verify(factory(), strict=True)
                self.assertTrue(result.ok, str(result))

    def test_save_load_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "demo.ft"
            build_led_blink("Demo").save(path)
            self.assertTrue(zipfile.is_zipfile(path))
            reloaded = Project.load(path)
            self.assertEqual(reloaded.name, "Demo")
            self.assertTrue(verify(reloaded, strict=True).ok)

    def test_statement_input_name_is_enforced(self) -> None:
        project = build_motor_run("Bad")
        project.put("/Bad.blockly", BAD_LOOP)
        result = verify(project, strict=True)
        self.assertFalse(result.ok)
        self.assertTrue(any("statement input must be" in c.label for c in result.checks))

    def test_correct_statement_input_passes(self) -> None:
        project = build_motor_run("Good")
        project.put("/Good.blockly", GOOD_LOOP)
        self.assertTrue(verify(project, strict=True).ok)

    def test_rename_moves_main_files(self) -> None:
        project = build_motor_run("Old")
        project.rename("New")
        self.assertIn("New.blockly", project.files())
        self.assertIn("New.py", project.files())
        self.assertNotIn("Old.blockly", project.files())

    def test_pin_block_and_instance_name(self) -> None:
        project = build_motor_run("Pins")
        ctrl = project.get_text("lib/controller.blockly")
        self.assertIn('<arg type="Motor" name="Motor-0" value="M1"/>', ctrl)
        self.assertIn('<block type="motor" id="pinMotor00000001"/>', ctrl)
        main = project.get_text("/Pins.blockly")
        self.assertIn("<field name=\"instance_name_0\">ctrl000000000001-pinMotor00000001</field>", main)

    def test_controller_python_matches_pins(self) -> None:
        project = build_motor_run("Pins")
        py = project.get_text("lib/controller.py")
        self.assertIn("TXT_M = txt_factory.controller_factory.create_graphical_controller()", py)
        self.assertIn("txt_factory.motor_factory.create_motor(TXT_M, 0)", py)

    def test_extract_and_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "demo.ft"
            build_motor_run("Demo").save(source)
            folder = Project.load(source).extract(Path(tmp) / "out")
            rebuilt = Project.from_directory(folder).save(Path(tmp) / "rebuilt.ft")
            self.assertTrue(verify(rebuilt, strict=True).ok)

    def test_builder_helpers(self) -> None:
        self.assertIn('statement name="DO"', build_motor_run("X").get_text("/X.blockly"))
        xml = controller_blockly("c", {"Motor": [("M1", "p")]})
        self.assertIn('value="M1"', xml)
        self.assertIn('type="motor_set_speed"', motor_set_speed("c", "p", 300))
        self.assertIn("300", wait_for(300))


class CliTests(unittest.TestCase):
    def _run(self, *args: str):
        """Run the CLI in-process and return (exit code, captured stdout)."""
        import contextlib
        import io

        from ftgateway.cli import main

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(list(args))
        return code, buffer.getvalue()

    def test_generate_and_verify(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run.ft"
            code, text = self._run(
                "gen", "motor-run", "--name", "Run", "--out", str(out), "--speed", "300"
            )
            self.assertEqual(code, 0, text)
            self.assertTrue(out.exists())
            code, text = self._run("verify", str(out), "--strict")
            self.assertEqual(code, 0, text)

    def test_blocks_command(self) -> None:
        code, text = self._run("blocks", "motor", "--limit", "5")
        self.assertEqual(code, 0)
        self.assertIn("motor_set_speed", text)


if __name__ == "__main__":
    unittest.main()
