# -*- coding: utf-8 -*-
"""校验器回归自测：好例必须过，坏例（块语句输入名写错）必须被拦。

用法：python selftest.py
"""
import subprocess
import sys
import tempfile
from pathlib import Path

FT = Path(r"C:\Users\MINT\.claude\skills\fischertechnik-ft\scripts\ft.py")
if not FT.exists():  # 允许在别处运行
    FT = Path(__file__).with_name("ft.py")
PY = sys.executable
SRC = Path(r"C:\Users\MINT\Desktop\慧鱼")

BAD = """<xml xmlns="https://developers.google.com/blockly/xml" version="23">
  <block type="start_block" id="S1" deletable="false" x="-400" y="-200">
    <statement name="statement">
      <block type="loop_endless" id="L1">
        <statement name="statement">
          <block type="util_python" id="U1"><field name="value">x = 1</field></block>
        </statement>
      </block>
    </statement>
  </block>
</xml>
"""

GOOD = BAD.replace('<statement name="statement">\n          <block type="util_python"',
                   '<statement name="DO">\n          <block type="util_python"')


def run(*a):
    r = subprocess.run([str(x) for x in a], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def build(tmp, name, xml):
    ft = tmp / f"{name}.ft"
    run(PY, FT, "new", ft, "--name", name, "--template", "blocks")
    src = tmp / f"{name}.blockly"
    src.write_text(xml, encoding="utf-8", newline="\n")
    run(PY, FT, "put", ft, f"/{name}.blockly", src)
    return ft


def main():
    tmp = Path(tempfile.mkdtemp())

    rc, txt = run(PY, FT, "verify", build(tmp, "Bad", BAD), "--quiet")
    print("负例退出码:", rc, "(应为非 0)")
    for line in txt.strip().splitlines():
        if "语句输入名" in line or "RESULT" in line:
            print("   ", line.strip())
    assert rc != 0, "负例未被拦截"

    rc, txt = run(PY, FT, "verify", build(tmp, "Good", GOOD), "--strict", "--quiet")
    print("正例退出码:", rc, "(应为 0)")
    assert rc == 0, "正例被误判"

    live = [p for p in SRC.glob("*.ft") if p.exists()]
    if live:
        rc, txt = run(PY, FT, "verify", *live, "--strict", "--quiet")
        print("现有工程:", [p.name for p in live], "->", "OK" if rc == 0 else "FAIL")
        assert rc == 0, "现有工程校验失败"

    print("ALL REGRESSION CHECKS PASSED")


if __name__ == "__main__":
    main()
