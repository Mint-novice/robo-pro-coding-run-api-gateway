#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ft.py — fischertechnik ROBO Pro Coding 工程文件 (.ft) 读写 / 配置 / 校验 / 脚手架工具。

.ft 就是一个 ZIP，官方布局：
    .project.json          项目元数据 (uuid/name/mode/version/controller/unsaved)
    lib/                   目录条目
    lib/controller.blockly 控制器块 (txt4_controller) —— 硬件接口声明
    lib/controller.py      由 controller.blockly 生成的 Python
    /<项目名>.blockly      主程序 Blockly XML
    /<项目名>.py           主程序 Python（图形化模式下属生成物）

子命令：
    info     FILE                          打印结构、元数据、块/代码统计
    ls       FILE                          仅列条目
    extract  FILE OUTDIR                   解出全部条目
    pack     INDIR OUT [--name N] [--mode M] [--controller C]
    new      OUT --name N [--mode M] [--template blocks|python]
    config   FILE [--name N] [--mode M] [--controller C] [--uuid U] [--unsaved 0|1]
    get      FILE ENTRY [--out PATH]
    put      FILE ENTRY SRC                用 SRC 文件内容替换/新增条目
    verify   FILE... [--strict]
"""
from __future__ import annotations

import argparse
import json
import os
import py_compile
import re
import shutil
import sys
import tempfile
import time
import uuid
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
ASSETS = SKILL / "assets"
CATALOG = SKILL / "references" / "block-catalog.json"

PROJECT_JSON = ".project.json"
DEFAULT_ENTRY_ORDER_HEAD = [PROJECT_JSON, "lib/"]
MODES = ("ADVANCED", "PROFESSIONAL", "UNDEFINED")
CONTROLLERS = ("TXT4", "RX", "BT_SMART")


def out(msg=""):
    print(msg)


def norm(name: str) -> str:
    """条目名归一化：去掉前导 '/'，统一用 '/' 分隔。"""
    return name.replace("\\", "/").lstrip("/")


def is_dir_entry(name: str) -> bool:
    return name.endswith("/")


# --------------------------------------------------------------------------
# zip 读写
# --------------------------------------------------------------------------
def read_entries(path: Path):
    """返回 [(原始条目名, bytes|None)]，保持原顺序；None 表示目录条目。"""
    items = []
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad is not None:
            raise SystemExit(f"[!] ZIP CRC 损坏: {bad}")
        for info in z.infolist():
            items.append(
                (info.filename, None if info.is_dir() else z.read(info.filename))
            )
    return items


def _zipinfo(name: str, is_dir: bool):
    zi = zipfile.ZipInfo(name, date_time=time.localtime()[:6])
    zi.compress_type = zipfile.ZIP_DEFLATED
    zi.external_attr = ((0o40775 << 16) | 0x10) if is_dir else (0o664 << 16)
    return zi


def write_entries(path: Path, items):
    if path.exists():
        path.unlink()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in items:
            if data is None or is_dir_entry(name):
                z.writestr(_zipinfo(name, True), b"")
            else:
                z.writestr(_zipinfo(name, False), data)


def find_entry(items, wanted: str):
    """按归一化名字找条目，返回索引。"""
    w = norm(wanted)
    for i, (name, _) in enumerate(items):
        if norm(name) == w:
            return i
    return -1


def get_config(items) -> dict:
    i = find_entry(items, PROJECT_JSON)
    if i < 0:
        raise SystemExit("[!] 缺少 .project.json")
    return json.loads(items[i][1].decode("utf-8"))


def set_config(items, cfg: dict):
    i = find_entry(items, PROJECT_JSON)
    data = json.dumps(cfg, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if i < 0:
        items.insert(0, (PROJECT_JSON, data))
    else:
        items[i] = (items[i][0], data)


def load_catalog() -> dict:
    if CATALOG.exists():
        try:
            return json.loads(CATALOG.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def project_prefix(cfg: dict) -> str:
    """主文件名（不含扩展名）。"""
    return cfg.get("name") or "Main"


# --------------------------------------------------------------------------
# 子命令
# --------------------------------------------------------------------------
def cmd_ls(args):
    for name, data in read_entries(Path(args.file)):
        if data is None:
            out(f"{'<dir>':>9}  {name}")
        else:
            out(f"{len(data):>9}  {name}")


def cmd_info(args):
    p = Path(args.file)
    items = read_entries(p)
    cfg = get_config(items)
    out(f"file       : {p}  ({p.stat().st_size} bytes)")
    out(f"project    : {json.dumps(cfg, ensure_ascii=False)}")
    out(f"entry count: {len(items)}")
    for name, data in items:
        if data is None:
            out(f"  <dir>      {name}")
            continue
        kind = Path(norm(name)).suffix.lower() or "(none)"
        extra = ""
        if kind == ".blockly":
            try:
                root = ET.fromstring(data)
                blocks = [b.get("type") for b in root.iter() if norm_tag(b.tag) == "block"]
                extra = f"blocks={blocks}"
            except Exception as ex:
                extra = f"XML 解析失败: {ex}"
        elif kind == ".py":
            extra = f"{data.count(chr(10).encode()) + 1} 行"
        elif kind == ".json":
            try:
                extra = f"keys={list(json.loads(data.decode('utf-8')).keys())}"
            except Exception as ex:
                extra = f"JSON 解析失败: {ex}"
        out(f"  {len(data):>7} B  {name:28} {extra}")


def norm_tag(tag: str) -> str:
    return tag.split("}")[-1]


PIN_FIELD_RE = re.compile(r"^(Input|Output|Motor|Servomotor|Counter|I2C|USB)-\d+$")


def check_input_names(root, cat) -> dict:
    """校验 <statement name> / <value name> / <field name> 是否是官方块定义里存在的输入名。

    statement 名写错 → Blockly 直接丢弃里面的块（用户看到空循环）。
    value/field 名同理，但部分块用 mutation 动态生成输入，故 value/field 只告警。
    """
    stmt = {s.lower() for s in cat.get("statement_inputs", [])}
    vals = {s.lower() for s in cat.get("value_inputs", [])}
    fields = {s.lower() for s in cat.get("field_names", [])}
    block_stmt = cat.get("block_statement_inputs", {})
    pin_field = {p.lower() + "-" for p in cat.get("pin_types", {})} | {
        "input-", "output-", "motor-", "servomotor-", "counter-", "i2c-", "usb-"
    }
    bad = {"statement": [], "value": []}

    # 1) 块级检查：块类型决定它能接受哪个语句输入名（写错 → 子块被静默丢弃）
    for blk in root.iter():
        if norm_tag(blk.tag) != "block":
            continue
        types = blk.get("type")
        allowed = block_stmt.get(types)
        if not allowed:
            continue
        for child in blk:
            if norm_tag(child.tag) != "statement":
                continue
            got = child.get("name") or ""
            if got not in allowed:
                bad["statement"].append(
                    f'<block type="{types}"> 的语句输入名应为 {allowed}，写成了 "{got}" —— 里面的块会被丢弃'
                )

    for el in root.iter():
        tag = norm_tag(el.tag)
        name = el.get("name")
        if not name:
            continue
        low = name.lower()
        if tag == "statement":
            if stmt and low not in stmt:
                bad["statement"].append(
                    f'<statement name="{name}"> 不是官方语句输入名（应为 {sorted(stmt)}），块会被丢弃'
                )
        elif tag == "value":
            if vals and low not in vals and not any(low.startswith(p) for p in pin_field):
                bad["value"].append(f'<value name="{name}"> 不在官方值输入名清单里')
        elif tag == "field":
            if fields and low not in fields and not PIN_FIELD_RE.match(name) and not re.match(
                r"^(instance_name|direction)_\d+$", name
            ):
                bad["value"].append(f'<field name="{name}"> 不在官方字段名清单里')
    return bad


def cmd_extract(args):
    src = Path(args.file)
    dst = Path(args.outdir)
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for name, data in read_entries(src):
        target = dst / norm(name)
        if data is None:
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        n += 1
    out(f"解出 {n} 个文件 -> {dst}")


def collect_dir(src: Path):
    """把解压目录重新组织成官方条目顺序（主文件加前导 '/'）。"""
    items = []
    if not (src / PROJECT_JSON).exists():
        raise SystemExit(f"[!] {src} 下没有 {PROJECT_JSON}")
    items.append((PROJECT_JSON, (src / PROJECT_JSON).read_bytes()))
    libdir = src / "lib"
    if libdir.is_dir():
        items.append(("lib/", None))
        for f in sorted(libdir.rglob("*")):
            if f.is_dir():
                items.append((norm(str(f.relative_to(src))) + "/", None))
            else:
                items.append((norm(str(f.relative_to(src))), f.read_bytes()))
    mains = sorted(
        f
        for f in src.iterdir()
        if f.is_file() and f.suffix.lower() in (".py", ".blockly", ".xml", ".json")
        and f.name != PROJECT_JSON
    )
    for f in mains:
        items.append(("/" + f.name, f.read_bytes()))
    return items


def cmd_pack(args):
    src = Path(args.indir)
    items = collect_dir(src)
    if args.name or args.mode or args.controller:
        cfg = json.loads(items[0][1].decode("utf-8"))
        if args.name:
            cfg["name"] = args.name
        if args.mode:
            cfg["mode"] = args.mode
        if args.controller:
            cfg["controller"] = args.controller
        cfg.setdefault("uuid", str(uuid.uuid4()))
        cfg.setdefault("version", "1.0")
        cfg["unsaved"] = False
        items[0] = (PROJECT_JSON, json.dumps(cfg, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    p = Path(args.out)
    write_entries(p, items)
    out(f"打包 -> {p}  ({p.stat().st_size} bytes, {len(items)} 条目)")
    run_verify([p], strict=False, quiet=False)


def render_template(text: str, cfg: dict) -> str:
    repl = {
        "{{NAME}}": project_prefix(cfg),
        "{{MODULE}}": re.sub(r"[^0-9A-Za-z_]", "_", project_prefix(cfg)),
        "{{UUID}}": cfg.get("uuid", str(uuid.uuid4())),
        "{{MODE}}": cfg.get("mode", "ADVANCED"),
        "{{CONTROLLER}}": cfg.get("controller", "TXT4"),
    }
    for k, v in repl.items():
        text = text.replace(k, str(v))
    return text


def cmd_new(args):
    tpl = args.template
    mode = args.mode or ("PROFESSIONAL" if tpl == "python" else "ADVANCED")
    name = args.name
    cfg = {
        "uuid": str(uuid.uuid4()),
        "name": name,
        "mode": mode,
        "version": "1.0",
        "controller": args.controller,
        "unsaved": False,
    }
    items = [
        (PROJECT_JSON, json.dumps(cfg, separators=(",", ":"), ensure_ascii=False).encode("utf-8")),
        ("lib/", None),
        ("lib/controller.py", (ASSETS / "controller.py").read_bytes()),
    ]
    if tpl == "python":
        body = (ASSETS / "main.python.py").read_text(encoding="utf-8")
        items.append((f"/{name}.py", render_template(body, cfg).encode("utf-8")))
    else:
        items.append(("lib/controller.blockly", (ASSETS / "controller.blockly").read_bytes()))
        body = (ASSETS / "main.blocks.xml").read_text(encoding="utf-8")
        items.append((f"/{name}.blockly", render_template(body, cfg).encode("utf-8")))
        body = (ASSETS / "main.blocks.py").read_text(encoding="utf-8")
        items.append((f"/{name}.py", render_template(body, cfg).encode("utf-8")))
    p = Path(args.out)
    write_entries(p, items)
    out(f"新建 -> {p}  (mode={mode}, controller={args.controller}, {len(items)} 条目)")
    run_verify([p], strict=False, quiet=False)


def cmd_config(args):
    p = Path(args.file)
    items = read_entries(p)
    cfg = get_config(items)
    before = json.dumps(cfg, ensure_ascii=False)
    if args.name:
        cfg["name"] = args.name
    if args.mode:
        cfg["mode"] = args.mode
    if args.controller:
        cfg["controller"] = args.controller
    if args.uuid:
        cfg["uuid"] = args.uuid
    if args.unsaved is not None:
        cfg["unsaved"] = bool(args.unsaved)
    cfg.setdefault("version", "1.0")
    set_config(items, cfg)
    # 主文件跟着改名：/<旧名>.py -> /<新名>.py
    if args.name:
        old = json.loads(before)["name"] if "name" in json.loads(before) else None
        if old and old != args.name:
            for ext in (".py", ".blockly"):
                i = find_entry(items, f"/{old}{ext}")
                if i >= 0:
                    items[i] = (f"/{args.name}{ext}", items[i][1])
    write_entries(p, items)
    out(f"配置已写入 {p}: {json.dumps(cfg, ensure_ascii=False)}")


def cmd_get(args):
    items = read_entries(Path(args.file))
    i = find_entry(items, args.entry)
    if i < 0:
        raise SystemExit(f"[!] 找不到条目 {args.entry}")
    data = items[i][1]
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_bytes(data)
        out(f"-> {args.out} ({len(data)} bytes)")
    else:
        sys.stdout.write(data.decode("utf-8", "replace"))


def cmd_put(args):
    p = Path(args.file)
    items = read_entries(p)
    data = Path(args.src).read_bytes()
    i = find_entry(items, args.entry)
    if i < 0:
        name = args.entry if args.entry.startswith("/") else "/" + norm(args.entry)
        items.append((name, data))
        out(f"新增条目 {name}")
    else:
        items[i] = (items[i][0], data)
        out(f"替换条目 {items[i][0]}")
    write_entries(p, items)


# --------------------------------------------------------------------------
# 校验
# --------------------------------------------------------------------------
def run_verify(files, strict=False, quiet=False) -> bool:
    cat = load_catalog()
    known_blocks = set(cat.get("block_types", [])) | set(cat.get("hardware_types", []))
    ok = True
    for f in files:
        p = Path(f)
        if not quiet:
            out("=" * 72)
            out(f"校验 {p}")
        if not p.exists():
            out("  [FAIL] 文件不存在")
            ok = False
            continue
        try:
            items = read_entries(p)
        except SystemExit as ex:
            out(f"  [FAIL] {ex}")
            ok = False
            continue
        names = [norm(n) for n, _ in items]
        checks = []

        has_cfg = PROJECT_JSON in names
        checks.append(("有 .project.json", has_cfg))
        cfg = {}
        if has_cfg:
            try:
                cfg = get_config(items)
                checks.append(("project.json 可解析", True))
                missing = [k for k in ("uuid", "name", "mode", "version", "controller") if k not in cfg]
                checks.append((f"元数据字段齐全{' ' + str(missing) if missing else ''}", not missing))
                checks.append((f"mode 合法 ({cfg.get('mode')})", cfg.get("mode") in MODES))
                checks.append((f"controller 合法 ({cfg.get('controller')})", cfg.get("controller") in CONTROLLERS))
            except Exception as ex:
                checks.append((f"project.json 可解析 ({ex})", False))

        name = cfg.get("name")
        modes = cfg.get("mode")
        if name:
            if modes == "PROFESSIONAL":
                checks.append((f"有主程序 /{name}.py", f"{name}.py" in names))
            else:
                checks.append((f"有主程序 /{name}.blockly", f"{name}.blockly" in names))

        for n in names:
            if n.endswith(".json") and n != PROJECT_JSON:
                try:
                    json.loads(dict((norm(a), b) for a, b in items)[n].decode("utf-8"))
                    checks.append((f"{n} JSON 合法", True))
                except Exception as ex:
                    checks.append((f"{n} JSON 合法 ({ex})", False))

        blocks_total = []
        for n, data in items:
            if not n.endswith(".blockly"):
                continue
            try:
                root = ET.fromstring(data)
                types = [b.get("type") for b in root.iter() if norm_tag(b.tag) == "block"]
                blocks_total += types
                checks.append((f"{norm(n)} XML 合法", True))
                if modes and modes != "PROFESSIONAL" and norm(n) == f"{name}.blockly":
                    checks.append(("主程序含 start_block", "start_block" in types))
                unknown = [t for t in types if known_blocks and t not in known_blocks]
                if unknown:
                    msg = f"{norm(n)} 未在官方块清单中的块类型 {unknown}"
                    if strict:
                        checks.append((msg, False))
                    else:
                        out(f"  [warn] {msg}")
                # 语句/值输入名写错时 Blockly 会静默丢弃子块 —— 必须拦
                bad_inputs = check_input_names(root, cat)
                for msg in bad_inputs["statement"]:
                    checks.append((f"{norm(n)} {msg}", False))
                for msg in bad_inputs["value"]:
                    out(f"  [warn] {norm(n)} {msg}")
            except Exception as ex:
                checks.append((f"{norm(n)} XML 合法 ({ex})", False))

        with tempfile.TemporaryDirectory() as td:
            for n, data in items:
                if not n.endswith(".py"):
                    continue
                tp = Path(td) / ("x_" + norm(n).replace("/", "_"))
                tp.write_bytes(data)
                try:
                    py_compile.compile(str(tp), cfile=str(tp) + "c", doraise=True)
                    checks.append((f"{norm(n)} Python 语法", True))
                except Exception as ex:
                    checks.append((f"{norm(n)} Python 语法 ({ex})", False))

        for label, passed in checks:
            if not quiet or not passed:
                out(f"  [{'OK ' if passed else 'FAIL'}] {label}")
            ok = ok and passed
    return ok


def cmd_verify(args):
    ok = run_verify(args.files, strict=args.strict, quiet=args.quiet)
    out("=" * 72)
    out("RESULT: " + ("ALL CHECKS PASSED" if ok else "FAILURES PRESENT"))
    raise SystemExit(0 if ok else 1)


# --------------------------------------------------------------------------
def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(prog="ft.py", description="慧鱼 ROBO Pro Coding .ft 工程工具")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ls", help="列出条目")
    p.add_argument("file")
    p.set_defaults(func=cmd_ls)

    p = sub.add_parser("info", help="结构 + 元数据 + 统计")
    p.add_argument("file")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("extract", help="解压到目录")
    p.add_argument("file")
    p.add_argument("outdir")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("pack", help="从目录打包成 .ft")
    p.add_argument("indir")
    p.add_argument("out")
    p.add_argument("--name")
    p.add_argument("--mode", choices=MODES)
    p.add_argument("--controller", choices=CONTROLLERS)
    p.set_defaults(func=cmd_pack)

    p = sub.add_parser("new", help="生成脚手架工程")
    p.add_argument("out")
    p.add_argument("--name", required=True)
    p.add_argument("--mode", choices=MODES)
    p.add_argument("--controller", default="TXT4", choices=CONTROLLERS)
    p.add_argument("--template", default="blocks", choices=("blocks", "python"))
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("config", help="改项目元数据")
    p.add_argument("file")
    p.add_argument("--name")
    p.add_argument("--mode", choices=MODES)
    p.add_argument("--controller", choices=CONTROLLERS)
    p.add_argument("--uuid")
    p.add_argument("--unsaved", type=int, choices=(0, 1))
    p.set_defaults(func=cmd_config)

    p = sub.add_parser("get", help="读单个条目")
    p.add_argument("file")
    p.add_argument("entry")
    p.add_argument("--out")
    p.set_defaults(func=cmd_get)

    p = sub.add_parser("put", help="写单个条目")
    p.add_argument("file")
    p.add_argument("entry")
    p.add_argument("src")
    p.set_defaults(func=cmd_put)

    p = sub.add_parser("verify", help="校验 .ft")
    p.add_argument("files", nargs="+")
    p.add_argument("--strict", action="store_true", help="未知块类型视为失败")
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_verify)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
