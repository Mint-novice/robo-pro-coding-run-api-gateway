"""Command line interface: ``ftg`` (or ``python -m ftgateway``)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .blocks import (
    ProjectBuilder,
    build_led_blink,
    build_led_steady,
    build_motor_run,
    build_python_project,
)
from .project import CONTROLLERS, MODES, Project, ProjectError
from .verify import verify


def _print(text: str = "") -> None:
    print(text)


# --------------------------------------------------------------------- commands
def cmd_info(args: argparse.Namespace) -> int:
    project = Project.load(args.file)
    cfg = project.config
    _print(f"file       : {args.file}")
    _print(f"project    : {json.dumps(cfg, ensure_ascii=False)}")
    _print(f"entries    : {len(project.items)}")
    for name, data in project.items:
        if data is None:
            _print(f"  <dir>      {name}")
            continue
        detail = ""
        if name.endswith(".blockly"):
            import xml.etree.ElementTree as ET

            try:
                root = ET.fromstring(data)
                types = [b.get("type") for b in root.iter() if b.tag.split("}")[-1] == "block"]
                detail = f"blocks={types}"
            except ET.ParseError as exc:
                detail = f"XML error: {exc}"
        elif name.endswith(".py"):
            detail = f"{len(data.splitlines())} lines"
        _print(f"  {len(data):>7} B  {name:26} {detail}")
    return 0


def cmd_ls(args: argparse.Namespace) -> int:
    for name, data in Project.load(args.file).items:
        _print(f"{'<dir>' if data is None else len(data):>9}  {name}")
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    project = Project.load(args.file)
    project.extract(args.outdir)
    _print(f"extracted {len(project.items)} entries -> {args.outdir}")
    return 0


def cmd_pack(args: argparse.Namespace) -> int:
    project = Project.from_directory(args.indir)
    if args.name:
        project.rename(args.name)
    if args.mode:
        cfg = dict(project.config)
        cfg["mode"] = args.mode
        project.config = cfg
    if args.controller:
        cfg = dict(project.config)
        cfg["controller"] = args.controller
        project.config = cfg
    path = project.save(args.out)
    _print(f"packed -> {path} ({path.stat().st_size} bytes)")
    result = verify(path)
    _print(str(result))
    return 0 if result.ok else 1


def cmd_config(args: argparse.Namespace) -> int:
    project = Project.load(args.file)
    if args.name:
        project.rename(args.name)
    cfg = dict(project.config)
    if args.mode:
        cfg["mode"] = args.mode
    if args.controller:
        cfg["controller"] = args.controller
    if args.uuid:
        cfg["uuid"] = args.uuid
    if args.unsaved is not None:
        cfg["unsaved"] = bool(args.unsaved)
    project.config = cfg
    project.save(args.file)
    _print(json.dumps(project.config, ensure_ascii=False))
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    data = Project.load(args.file).get(args.entry)
    if args.out:
        Path(args.out).write_bytes(data)
        _print(f"-> {args.out} ({len(data)} bytes)")
    else:
        sys.stdout.write(data.decode("utf-8", "replace"))
    return 0


def cmd_put(args: argparse.Namespace) -> int:
    project = Project.load(args.file)
    project.put(args.entry, Path(args.src).read_bytes())
    project.save(args.file)
    _print(f"wrote {args.entry}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    ok = True
    for file in args.files:
        result = verify(file, strict=args.strict)
        _print("=" * 72)
        _print(f"verify {file}")
        _print(str(result))
        ok = ok and result.ok
    _print("=" * 72)
    _print("RESULT: " + ("ALL CHECKS PASSED" if ok else "FAILURES PRESENT"))
    return 0 if ok else 1


def cmd_gen(args: argparse.Namespace) -> int:
    kind = args.kind
    if kind == "motor-run":
        project = build_motor_run(args.name, speed=args.speed, direction=args.direction, hold=args.hold)
    elif kind == "led-blink":
        project = build_led_blink(args.name, speed=args.speed, hold=args.hold)
    elif kind == "led-on":
        project = build_led_steady(args.name, speed=args.speed)
    elif kind == "python":
        project = build_python_project(args.name)
    else:  # pragma: no cover - argparse choices guard this
        raise ProjectError(f"unknown recipe: {kind}")

    out = Path(args.out or f"{args.name}.ft")
    project.save(out)
    _print(f"generated {out} ({out.stat().st_size} bytes)")
    result = verify(out, strict=True)
    _print(str(result))
    return 0 if result.ok else 1


def cmd_new(args: argparse.Namespace) -> int:
    project = Project.create(args.name, mode=args.mode, controller=args.controller)
    builder = ProjectBuilder(args.name, controller=args.controller)
    builder.add_motor("M1")
    project = builder.build()
    out = Path(args.out)
    project.save(out)
    _print(f"created {out}")
    _print(str(verify(out)))
    return 0


def cmd_blocks(args: argparse.Namespace) -> int:
    from .verify import block_schema

    schema = block_schema()
    pattern = (args.filter or "").lower()
    hits = 0
    for block_type in sorted(schema):
        entry = schema[block_type]
        title = str(entry.get("title") or "")
        if pattern and pattern not in block_type.lower() and pattern not in title.lower():
            continue
        hits += 1
        inputs = ", ".join(i.get("name") or "?" for i in entry.get("inputs", []) if i.get("name"))
        fields = ", ".join(f.get("name") or "?" for f in entry.get("fields", []) if f.get("name"))
        _print(f"{block_type:36} {title[:44]:46} inputs=[{inputs}] fields=[{fields}]")
        if hits >= args.limit:
            break
    _print(f"-- {hits} block(s)")
    return 0


# ------------------------------------------------------------------------ args
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ftg",
        description="Fischertechnik ROBO Pro Coding (.ft) project toolkit",
    )
    parser.add_argument("--version", action="version", version=f"ftg {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("info", help="show structure and metadata")
    p.add_argument("file")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("ls", help="list entries")
    p.add_argument("file")
    p.set_defaults(func=cmd_ls)

    p = sub.add_parser("extract", help="unpack a project")
    p.add_argument("file")
    p.add_argument("outdir")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("pack", help="repack a project from a folder")
    p.add_argument("indir")
    p.add_argument("out")
    p.add_argument("--name")
    p.add_argument("--mode", choices=MODES)
    p.add_argument("--controller", choices=CONTROLLERS)
    p.set_defaults(func=cmd_pack)

    p = sub.add_parser("new", help="create an empty graphical project")
    p.add_argument("out")
    p.add_argument("--name", required=True)
    p.add_argument("--mode", default="ADVANCED", choices=MODES)
    p.add_argument("--controller", default="TXT4", choices=CONTROLLERS)
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("config", help="change project metadata")
    p.add_argument("file")
    p.add_argument("--name")
    p.add_argument("--mode", choices=MODES)
    p.add_argument("--controller", choices=CONTROLLERS)
    p.add_argument("--uuid")
    p.add_argument("--unsaved", type=int, choices=(0, 1))
    p.set_defaults(func=cmd_config)

    p = sub.add_parser("get", help="read one entry")
    p.add_argument("file")
    p.add_argument("entry")
    p.add_argument("--out")
    p.set_defaults(func=cmd_get)

    p = sub.add_parser("put", help="replace one entry")
    p.add_argument("file")
    p.add_argument("entry")
    p.add_argument("src")
    p.set_defaults(func=cmd_put)

    p = sub.add_parser("verify", help="static verification")
    p.add_argument("files", nargs="+")
    p.add_argument("--strict", action="store_true")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("gen", help="generate a ready-to-run project")
    p.add_argument("kind", choices=("motor-run", "led-blink", "led-on", "python"))
    p.add_argument("--name", default="Program")
    p.add_argument("--out")
    p.add_argument("--speed", type=int, default=512)
    p.add_argument("--direction", default="Motor.CW", choices=("Motor.CW", "Motor.CCW"))
    p.add_argument("--hold", type=float, default=0.1)
    p.set_defaults(func=cmd_gen)

    p = sub.add_parser("blocks", help="search the block catalog")
    p.add_argument("filter", nargs="?")
    p.add_argument("--limit", type=int, default=40)
    p.set_defaults(func=cmd_blocks)

    return parser


def main(argv: list | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):  # pragma: no cover
        pass
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ProjectError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
