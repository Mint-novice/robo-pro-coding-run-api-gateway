#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dump_catalog.py — 从已安装的 ROBO Pro Coding (Electron) app.asar 里提取官方
Blockly 块类型 / 硬件类型 / 字段名常量，生成 references/block-catalog.json。

app 升级后重跑即可刷新清单：
    python dump_catalog.py                 # 自动探测安装路径
    python dump_catalog.py --asar PATH     # 指定 app.asar
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE.parent / "references" / "block-catalog.json"

CANDIDATES = [
    r"C:\Users\%USERNAME%\AppData\Local\Programs\ROBOProCoding-zh\app\resources\app.asar",
    r"C:\Users\%USERNAME%\AppData\Local\Programs\ROBO Pro Coding\resources\app.asar",
    r"C:\Program Files\ROBO Pro Coding\resources\app.asar",
    r"C:\Program Files (x86)\ROBO Pro Coding\resources\app.asar",
]


def find_asar(explicit=None) -> Path:
    if explicit:
        p = Path(explicit)
        if p.exists():
            return p
        raise SystemExit(f"[!] 找不到 {p}")
    import os

    for c in CANDIDATES:
        p = Path(os.path.expandvars(c.replace("%USERNAME%", os.environ.get("USERNAME", ""))))
        if p.exists():
            return p
    raise SystemExit("[!] 未找到 app.asar，请用 --asar 指定")


class Asar:
    def __init__(self, path: Path):
        self.path = path
        with open(path, "rb") as f:
            head = f.read(8)
            _, pickle_size = struct.unpack("<II", head)
            pickle = f.read(pickle_size)
        i0 = pickle.find(b"{")
        i1 = pickle.rfind(b"}")
        self.header = json.loads(pickle[i0 : i1 + 1].decode("utf-8", "replace"))
        self.base = 8 + pickle_size

    def find(self, predicate):
        hits = []

        def walk(node, prefix):
            for name, val in node.get("files", {}).items():
                p = prefix + "/" + name if prefix else name
                if "files" in val:
                    walk(val, p)
                elif predicate(p):
                    hits.append((p, val))

        walk(self.header, "")
        return hits

    def read(self, entry) -> bytes:
        size = int(entry["size"])
        offset = int(entry["offset"])
        with open(self.path, "rb") as f:
            f.seek(self.base + offset)
            return f.read(size)


def grab(text, start_marker, end_marker, regex=r'u\.([A-Z0-9_]+)="([^"]+)"'):
    i = text.find(start_marker)
    if i < 0:
        return {}
    j = text.find(end_marker, i)
    if j < 0:
        j = i + 8000
    seg = text[i:j]
    return {m.group(1): m.group(2) for m in re.finditer(regex, seg)}


def block_stmt_inputs(text, block_enum, fields) -> dict:
    """块类型 -> 它的语句输入名（从生成器 statementToCode(c,"X") 与 appendStatementInput 提取）。

    用于拦截 <statement name="..."> 写成其他块的名字：Blockly 会静默丢弃子块。
    """
    out = {}
    for const, block in block_enum.items():
        names = set()
        for m in re.finditer(r"ge\." + re.escape(const) + r"\b", text):
            seg = text[m.start() : m.start() + 1500]
            names |= set(re.findall(r'statementToCode\(\s*c\s*,\s*"([^"]+)"\s*\)', seg))
            names |= set(re.findall(r'appendStatementInput\("([^"]+)"\)', seg))
            for c in re.findall(r"statementToCode\(\s*c\s*,\s*G\.([A-Z0-9_]+)\s*\)", seg):
                if c in fields:
                    names.add(fields[c])
            for c in re.findall(r"appendStatementInput\(G\.([A-Z0-9_]+)\)", seg):
                if c in fields:
                    names.add(fields[c])
        if names:
            out[block] = sorted(names)
    return out


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--asar")
    ap.add_argument("--out", default=str(TARGET))
    args = ap.parse_args()

    asar = Asar(find_asar(args.asar))
    print("asar:", asar.path)
    mains = asar.find(lambda p: re.match(r"client/www/main\.[0-9a-f]+\.js$", p))
    if not mains:
        raise SystemExit("[!] asar 内没找到 client/www/main.*.js")
    path, entry = mains[0]
    text = asar.read(entry).decode("utf-8", "replace")
    print("bundle:", path, len(text), "chars")

    blocks = grab(text, 'u.START="start_block"', "}(ge||{})")
    hardware = grab(text, 'u.RX_CONTROLLER="rx_controller"', "}(At||{})")
    fields = grab(text, 'u.KEY="key"', "}(G||{})")

    # 引脚分类（txt4_controller 的 mutation arg type）：Input/Output/Motor/Servomotor/Counter/I2C/USB
    pins = {}
    for name in ("Input", "Output", "Motor", "Servomotor", "Counter", "I2C", "USB"):
        if f'"{name}"' in text:
            pins[name] = name

    # 语句输入名（<statement name="...">）：appendStatementInput("DO") / appendStatementInput(G.STATEMENT)
    stmt = set(re.findall(r'appendStatementInput\("([^"]+)"\)', text))
    stmt |= set(re.findall(r'type:"input_statement",\s*name:"([^"]+)"', text))
    for const in set(re.findall(r"appendStatementInput\(G\.([A-Z0-9_]+)\)", text)):
        if const in fields:
            stmt.add(fields[const])
    stmt |= set(fields[c] for c in set(re.findall(r'type:"input_statement",\s*name:G\.([A-Z0-9_]+)', text)) if c in fields)

    # 值输入名（<value name="...">）：input_value 的 name
    val = set(re.findall(r'type:"input_value",\s*name:"([^"]+)"', text))
    for const in set(re.findall(r'type:"input_value",\s*name:G\.([A-Z0-9_]+)', text)):
        if const in fields:
            val.add(fields[const])
    val |= set(re.findall(r'appendValueInput\("([^"]+)"\)', text))
    for const in set(re.findall(r"appendValueInput\(G\.([A-Z0-9_]+)\)", text)):
        if const in fields:
            val.add(fields[const])

    data = {
        "source": str(asar.path),
        "bundle": path,
        "description": "ROBO Pro Coding 官方 Blockly 块类型 / 硬件实例类型 / 字段名常量（自动提取）",
        "block_types": sorted(set(blocks.values())),
        "block_enum": blocks,
        "hardware_types": sorted(set(hardware.values())),
        "hardware_enum": hardware,
        "field_names": sorted(set(fields.values())),
        "field_enum": fields,
        "statement_inputs": sorted(stmt),
        "value_inputs": sorted(val),
        "block_statement_inputs": block_stmt_inputs(text, blocks, fields),
        "pin_types": pins,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"block_types={len(data['block_types'])} hardware_types={len(data['hardware_types'])} "
          f"field_names={len(data['field_names'])} -> {out}")


if __name__ == "__main__":
    main()
