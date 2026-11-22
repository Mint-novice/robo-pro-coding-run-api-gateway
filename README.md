# ROBO Pro Coding Run API Gateway

[![tests](https://img.shields.io/badge/tests-13%20passed-brightgreen)](tests/)
[![python](https://img.shields.io/badge/python-3.9%2B-blue)](pyproject.toml)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Targets ROBO Pro Coding 6.5.4** (Electron 31.7.7, TXT 4.0). Block ids and generator output are a
snapshot of that build; re-export with `bridge/dumpblocks.js` after an upgrade.

Generate, validate and drive **fischertechnik ROBO Pro Coding** projects (`.ft`) from Python.
A `.ft` file is a ZIP of JSON metadata, Blockly XML and Python — so a robot program can be
produced, diffed and tested like source code.

```bash
pip install -e .
ftg gen motor-run --name Motor_Run --speed 512    # motor on M1 turns forever
ftg verify Motor_Run.ft --strict                  # container, XML, block names, syntax
```

## CLI

| command | purpose |
|---|---|
| `ftg gen motor-run\|led-blink\|led-on\|python` | generate a ready-to-open project |
| `ftg verify FILE --strict` | offline validation (see below) |
| `ftg info FILE` · `ftg ls` | structure and metadata |
| `ftg extract` · `pack` · `get` · `put` · `config` | entry-level editing |
| `ftg blocks motor` | search the 314-block catalog |

No third-party dependencies; Python 3.9+.

## API

```python
from ftgateway import build_motor_run, verify
from ftgateway.blocks import ProjectBuilder

build_motor_run("Motor_Run", speed=512).save("Motor_Run.ft")
print(verify("Motor_Run.ft", strict=True))

b = ProjectBuilder("Conveyor")
b.add_motor("M1")
b.motor("M1", speed=300)
b.wait(2)
b.motor_off("M1")
b.build().save("Conveyor.ft")
```

## AI agent

Clone, then tell your agent:

> Read `AGENTS.md`, then build and verify my `.ft` programs with `ftg`.

`AGENTS.md` carries the format, the commands, the two silent-failure rules and the
verification loop. The 314-block dictionary in `src/ftgateway/data/` is the source of truth.
Optional skill: `./skills/install-skill.sh` (or `.ps1`).

## Bridge (optional, Windows)

Drives the installed application over the DevTools protocol — open a project, read the live
workspace, let the app generate the Python.

```powershell
.\bridge\launch.ps1 -Port 9334          # clears ELECTRON_RUN_AS_NODE, own profile
node bridge\setfile.js out.ft           # injects the file, no OS dialog
node bridge\verify_in_app.js ctrl.blockly main.blockly
node bridge\cdp.js shot proof.png
```

## Two failure modes it prevents

| trap | symptom | rule |
|---|---|---|
| wrong statement input | loop looks empty, no error | `loop_endless` takes `DO`; `start_block` takes `statement` |
| unmatched pin id | code becomes `-.set_speed(...)` | `instance_name_0` = `<controller-id>-<pin-block-id>` |

Both are encoded in `src/ftgateway/blocks.py` and enforced by `ftg verify`.

## Verified

| layer | evidence |
|---|---|
| container / metadata | unit tests, extract→pack round-trip (app 6.5.4) |
| block XML | parsed by the app's own Blockly inside the running process |
| generated Python | produced by the app's `pythonGenerator` |
| hardware | TXT 4.0: motor turns on M1, LED blinks on M1 |

## Layout

```
src/ftgateway/      library + CLI          bridge/     DevTools bridge
src/ftgateway/data/ block catalog+schema   docs/       format, bridge, blocks, troubleshooting
examples/           3 openable .ft         tests/      13 unit tests
```

## Legal

Unofficial third-party tool; no affiliation with or endorsement by fischertechnik GmbH or
beemo GmbH. Code and docs: MIT. `data/*.json` is interoperability metadata exported from a
locally installed application — UI wording and generated snippets belong to their owners and
are **not** covered by the MIT grant ([NOTICE.md](NOTICE.md)). No binaries, firmware, assets or
language packs are included. Back up your `.ft` files before using the bridge.

## Roadmap

`ftg upload` (run on the controller) · Python AST → blocks · sensor recipes.
