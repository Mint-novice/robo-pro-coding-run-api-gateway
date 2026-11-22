"""Static verification for `.ft` projects.

Checks performed (all offline, no application needed):

* container opens and every entry is readable
* ``.project.json`` parses and carries the required keys with legal values
* the main source file matching ``mode``/``name`` exists
* every ``.blockly`` file is valid XML
* every used block type exists in the catalog extracted from the real app
* statement input names match the per-block schema (a wrong name makes
  Blockly silently drop the children — the single most common breakage)
* every ``.py`` file compiles
"""

from __future__ import annotations

import json
import py_compile
import re
import tempfile
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Dict, List, Optional, Sequence
import xml.etree.ElementTree as ET

from .project import CONTROLLERS, MODES, Project, ProjectError, normalise

PIN_FIELD = re.compile(r"^(Input|Output|Motor|Servomotor|Counter|I2C|USB)-\d+$")
INDEXED_FIELD = re.compile(r"^(instance_name|direction)_\d+$")


def _load(name: str) -> Dict:
    try:
        text = resources.files("ftgateway.data").joinpath(name).read_text(encoding="utf-8")
    except (AttributeError, FileNotFoundError, ModuleNotFoundError):  # pragma: no cover
        path = Path(__file__).with_name("data") / name
        text = path.read_text(encoding="utf-8")
    return json.loads(text)


_CATALOG: Optional[Dict] = None
_SCHEMA: Optional[Dict] = None


def catalog() -> Dict:
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = _load("block-catalog.json")
    return _CATALOG


def block_schema() -> Dict[str, Dict]:
    global _SCHEMA
    if _SCHEMA is None:
        raw = _load("block-schema.json")
        _SCHEMA = {entry["type"]: entry for entry in raw.get("blocks", [])}
    return _SCHEMA


def known_block_types() -> set:
    cat = catalog()
    return set(cat.get("block_types", [])) | set(cat.get("hardware_types", []))


def statement_inputs_for(block_type: str) -> List[str]:
    return list(catalog().get("block_statement_inputs", {}).get(block_type, []))


def _tag(element: ET.Element) -> str:
    return element.tag.split("}")[-1]


@dataclass
class Check:
    label: str
    ok: bool


@dataclass
class VerifyResult:
    path: Optional[Path]
    checks: List[Check] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    def add(self, label: str, ok: bool) -> None:
        self.checks.append(Check(label, ok))

    def __str__(self) -> str:
        lines = [f"{'[OK ]' if c.ok else '[FAIL]'} {c.label}" for c in self.checks]
        lines += [f"[warn] {w}" for w in self.warnings]
        lines.append("RESULT: " + ("PASSED" if self.ok else "FAILED"))
        return "\n".join(lines)


def _check_blockly(name: str, text: str, result: VerifyResult, strict: bool, main: bool) -> None:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        result.add(f"{name}: XML parses ({exc})", False)
        return
    result.add(f"{name}: XML parses", True)

    types = [b.get("type") for b in root.iter() if _tag(b) == "block"]
    known = known_block_types()
    unknown = [t for t in types if t and known and t not in known]
    if unknown:
        if strict:
            result.add(f"{name}: unknown block types {unknown}", False)
        else:
            result.warnings.append(f"{name}: unknown block types {unknown}")

    if main:
        result.add(f"{name}: contains start_block", "start_block" in types)

    statement_checked = 0
    statement_bad = 0
    for block in root.iter():
        if _tag(block) != "block":
            continue
        block_type = block.get("type") or ""
        allowed = statement_inputs_for(block_type)
        if not allowed:
            continue
        for child in block:
            if _tag(child) != "statement":
                continue
            statement_checked += 1
            actual = child.get("name") or ""
            if actual not in allowed:
                statement_bad += 1
                result.add(
                    f'{name}: <block type="{block_type}"> statement input must be '
                    f'{allowed}, found "{actual}" — children would be dropped',
                    False,
                )
    if statement_checked and not statement_bad:
        result.add(
            f"{name}: statement input names match the block schema ({statement_checked})", True
        )

    for element in root.iter():
        if _tag(element) != "field":
            continue
        field_name = element.get("name") or ""
        if not field_name:
            continue
        if field_name in (catalog().get("field_names") or []):
            continue
        if PIN_FIELD.match(field_name) or INDEXED_FIELD.match(field_name):
            continue
        result.warnings.append(f'{name}: field "{field_name}" not in catalog')


def verify(path: str | Path | Project, strict: bool = False) -> VerifyResult:
    """Verify a project file (or an in-memory :class:`Project`)."""
    if isinstance(path, Project):
        project = path
        result = VerifyResult(None)
    else:
        result = VerifyResult(Path(path))
        try:
            project = Project.load(path)
        except ProjectError as exc:
            result.add(f"open container ({exc})", False)
            return result

    result.add("container opens", True)

    try:
        cfg = project.config
        result.add(".project.json parses", True)
        missing = [k for k in ("uuid", "name", "mode", "version", "controller") if k not in cfg]
        result.add(f"metadata complete{' ' + str(missing) if missing else ''}", not missing)
        result.add(f"mode legal ({cfg.get('mode')})", cfg.get("mode") in MODES)
        result.add(
            f"controller legal ({cfg.get('controller')})",
            cfg.get("controller") in CONTROLLERS,
        )
    except ProjectError as exc:
        result.add(f".project.json parses ({exc})", False)
        return result

    name = str(cfg.get("name"))
    mode = str(cfg.get("mode"))
    files = project.files()
    if mode == "PROFESSIONAL":
        result.add(f"main source /{name}.py exists", f"{name}.py" in files)
    else:
        result.add(f"main program /{name}.blockly exists", f"{name}.blockly" in files)

    for entry in files:
        if entry.endswith(".blockly"):
            _check_blockly(entry, project.get_text(entry), result, strict, entry == f"{name}.blockly")

    with tempfile.TemporaryDirectory() as tmp:
        for entry in files:
            if not entry.endswith(".py"):
                continue
            target = Path(tmp) / ("x_" + normalise(entry).replace("/", "_"))
            target.write_bytes(project.get(entry))
            try:
                py_compile.compile(str(target), cfile=str(target) + "c", doraise=True)
                result.add(f"{entry}: Python compiles", True)
            except py_compile.PyCompileError as exc:
                result.add(f"{entry}: Python compiles ({exc.msg.splitlines()[-1]})", False)
    return result
