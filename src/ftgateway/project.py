"""`.ft` project container: a ZIP with metadata, controller config and sources.

Layout produced by ROBO Pro Coding (verified against 6.5.x)::

    .project.json           project metadata
    lib/                    directory entry
    lib/controller.blockly  controller block (txt4_controller) — pin config
    lib/controller.py       generated Python for the controller
    /<name>.blockly         main program (Blockly XML)
    /<name>.py              main program Python

Main-file entries carry a leading ``/``; ``lib/`` entries do not.
Everything is UTF-8 with LF newlines.
"""

from __future__ import annotations

import json
import time
import uuid
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

CONFIG_NAME = ".project.json"
MODES = ("ADVANCED", "PROFESSIONAL", "UNDEFINED")
CONTROLLERS = ("TXT4", "RX", "BT_SMART")

Items = List[Tuple[str, Optional[bytes]]]


class ProjectError(RuntimeError):
    """Raised when a `.ft` file is malformed or cannot be built."""


def normalise(entry: str) -> str:
    """Strip leading slashes so ``/main.py`` and ``main.py`` compare equal."""
    return entry.replace("\\", "/").lstrip("/")


class Project:
    """In-memory representation of a `.ft` project."""

    def __init__(self, items: Iterable[Tuple[str, Optional[bytes]]]):
        self.items: Items = [(name, data) for name, data in items]

    # ---------------------------------------------------------------- load/save
    @classmethod
    def load(cls, path: str | Path) -> "Project":
        path = Path(path)
        if not path.exists():
            raise ProjectError(f"file not found: {path}")
        try:
            with zipfile.ZipFile(path) as zf:
                broken = zf.testzip()
                if broken is not None:
                    raise ProjectError(f"corrupt ZIP member: {broken}")
                items = [
                    (info.filename, None if info.is_dir() else zf.read(info.filename))
                    for info in zf.infolist()
                ]
        except zipfile.BadZipFile as exc:
            raise ProjectError(f"not a ZIP archive: {path}") from exc
        return cls(items)

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        if path.exists():
            path.unlink()
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, data in self.items:
                info = zipfile.ZipInfo(name, date_time=time.localtime()[:6])
                info.compress_type = zipfile.ZIP_DEFLATED
                if data is None or name.endswith("/"):
                    info.external_attr = (0o40775 << 16) | 0x10
                    zf.writestr(info, b"")
                else:
                    info.external_attr = 0o664 << 16
                    zf.writestr(info, data)
        return path

    @classmethod
    def from_directory(cls, directory: str | Path) -> "Project":
        """Rebuild a project from an extracted folder (``lib/`` + sources)."""
        directory = Path(directory)
        cfg_path = directory / CONFIG_NAME
        if not cfg_path.exists():
            raise ProjectError(f"{directory} has no {CONFIG_NAME}")
        items: Items = [(CONFIG_NAME, cfg_path.read_bytes())]
        lib = directory / "lib"
        if lib.is_dir():
            items.append(("lib/", None))
            for entry in sorted(lib.rglob("*")):
                rel = normalise(str(entry.relative_to(directory)))
                items.append((rel + "/", None) if entry.is_dir() else (rel, entry.read_bytes()))
        for entry in sorted(directory.iterdir()):
            if entry.is_file() and entry.name != CONFIG_NAME and entry.suffix in (".py", ".blockly"):
                items.append(("/" + entry.name, entry.read_bytes()))
        return cls(items)

    def extract(self, directory: str | Path) -> Path:
        directory = Path(directory)
        for name, data in self.items:
            target = directory / normalise(name)
            if data is None:
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        return directory

    # ------------------------------------------------------------------ access
    def entries(self) -> List[str]:
        return [name for name, _ in self.items]

    def files(self) -> List[str]:
        return [normalise(n) for n, d in self.items if d is not None]

    def _index(self, wanted: str) -> int:
        target = normalise(wanted)
        for index, (name, _) in enumerate(self.items):
            if normalise(name) == target:
                return index
        return -1

    def has(self, name: str) -> bool:
        return self._index(name) >= 0

    def get(self, name: str) -> bytes:
        index = self._index(name)
        if index < 0:
            raise ProjectError(f"entry not found: {name}")
        data = self.items[index][1]
        if data is None:
            raise ProjectError(f"{name} is a directory")
        return data

    def get_text(self, name: str) -> str:
        return self.get(name).decode("utf-8")

    def put(self, name: str, data: bytes | str, prefix_root: bool = True) -> None:
        if isinstance(data, str):
            data = data.encode("utf-8")
        index = self._index(name)
        if index >= 0:
            self.items[index] = (self.items[index][0], data)
            return
        entry = name if (name.startswith("/") or normalise(name).startswith("lib/")) else (
            "/" + normalise(name) if prefix_root else normalise(name)
        )
        self.items.append((entry, data))

    def remove(self, name: str) -> None:
        index = self._index(name)
        if index >= 0:
            del self.items[index]

    # --------------------------------------------------------------- metadata
    @property
    def config(self) -> Dict[str, object]:
        index = self._index(CONFIG_NAME)
        if index < 0:
            raise ProjectError(f"missing {CONFIG_NAME}")
        return json.loads(self.get_text(CONFIG_NAME))

    @config.setter
    def config(self, value: Dict[str, object]) -> None:
        blob = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        index = self._index(CONFIG_NAME)
        if index < 0:
            self.items.insert(0, (CONFIG_NAME, blob))
        else:
            self.items[index] = (CONFIG_NAME, blob)

    @property
    def name(self) -> str:
        return str(self.config.get("name") or "Main")

    @property
    def mode(self) -> str:
        return str(self.config.get("mode") or "ADVANCED")

    @property
    def controller(self) -> str:
        return str(self.config.get("controller") or "TXT4")

    def rename(self, new_name: str) -> None:
        old = self.name
        cfg = dict(self.config)
        cfg["name"] = new_name
        self.config = cfg
        if old != new_name:
            for ext in (".py", ".blockly"):
                index = self._index(f"/{old}{ext}")
                if index >= 0:
                    self.items[index] = (f"/{new_name}{ext}", self.items[index][1])

    # ------------------------------------------------------------------ build
    @classmethod
    def create(cls, name: str, mode: str = "ADVANCED", controller: str = "TXT4") -> "Project":
        if mode not in MODES:
            raise ProjectError(f"unknown mode: {mode}")
        if controller not in CONTROLLERS:
            raise ProjectError(f"unknown controller: {controller}")
        cfg = {
            "uuid": str(uuid.uuid4()),
            "name": name,
            "mode": mode,
            "version": "1.0",
            "controller": controller,
            "unsaved": False,
        }
        project = cls(
            [
                (CONFIG_NAME, json.dumps(cfg, separators=(",", ":"), ensure_ascii=False).encode("utf-8")),
                ("lib/", None),
            ]
        )
        return project

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Project {self.name!r} mode={self.mode} entries={len(self.items)}>"
