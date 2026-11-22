# Bridge: driving the real application

ROBO Pro Coding is an Electron app. With `--remote-debugging-port` it exposes
the Chrome DevTools Protocol, which is enough to script it end to end.

```text
launch.ps1 ──► app (Electron, CDP :9334)
                    ▲
        cdp.js ─────┤ eval / screenshot / click
     setfile.js ────┤ inject a .ft  (no OS dialog)
verify_in_app.js ───┤ parse blocks + generate Python with the app's own code
   dumpblocks.js ───┘ refresh the block catalog
```

## 1. Launch

```powershell
.\bridge\launch.ps1 -Port 9334
```

It shields you from two environment problems:

* **`ELECTRON_RUN_AS_NODE=1`** — if this variable is set (common on machines
  that also run other Electron tooling), the exe behaves like `node`: every
  argument is treated as a script path and the app exits immediately with
  `SyntaxError: Invalid or unexpected token` or `bad option: --user-data-dir`.
  The launcher clears the variable for the child process only:
  `cmd /c "set ELECTRON_RUN_AS_NODE=&& start "" app.exe --remote-debugging-port=…"`.
* **single-instance lock** — a dedicated `--user-data-dir` gives the bridge its
  own instance, so it never fights with the window you use by hand.

## 2. Talk to it

```bash
node bridge/cdp.js list
node bridge/cdp.js eval "document.body.innerText"
node bridge/cdp.js shot shot.png
node bridge/inject.js some-script.js          # run a file inside the renderer
node bridge/click.js 470 299                  # real mouse click at viewport coords
```

`inject.js` wraps your script in an async IIFE and returns the JSON value, so a
probe file can `return {...}` and you get it on stdout.

## 3. Open a project without any dialog

The app's “load project” stepper ends in a hidden `<input type=file>`. That is
the whole trick:

```bash
node bridge/setfile.js examples/motor-run.ft
```

Internally: `DOM.getDocument` → `DOM.querySelector('input[type=file]')` →
`DOM.setFileInputFiles`. No native file picker, no coordinates, no SendKeys.

(The UI path still needs two clicks to get there — “加载项目…” → “本地” →
“下一步” — because the input only exists on that step. `click.js` drives those
by viewport coordinates taken from `getBoundingClientRect()`.)

## 4. Use the app as the reference implementation

```bash
node bridge/verify_in_app.js ctrl.blockly main.blockly
```

This evaluates in the renderer:

```js
const req = (() => { let r;
  window.webpackChunkangular_electron.push([[Symbol()], {}, (x) => { r = x; }]);
  return r; })();
const B  = req(3375);            // full Blockly namespace
const PG = req(8299).pythonGenerator;
```

* `B.Xml.domToWorkspace(...)` — parse our XML with the app's own registry
* `B.Workspace.getAll()` — inspect the *live* workspace of the open project
* `PG.workspaceToCode(ws)` — generate exactly what the app would upload

Result for a motor program: `TXT_M_M1_motor.set_speed(int(512), Motor.CW)`.

## 5. Refresh the block catalog

```bash
node bridge/dumpblocks.js src/ftgateway/data/block-schema.json
```

Iterates every registered block in a headless workspace and records type, title
(Chinese), statement/value inputs, fields and the Python the block emits.
Part of the output is used by `ftg verify` to reject wrong statement-input names.

## What the preload bridge exposes

```json
{
  "_cdvElectronExecution":  ["executeCommand", "getWindowId", "openNewWindow", "closeWindow", "toggleDevTools", "…"],
  "_cdvElectronFileSystem": ["showSaveDialog", "writeFileSync"],
  "_cdvElectronSetting":    ["setSync", "getSync"]
}
```

`executeCommand` runs in the main process — the closest thing this app has to
an official SDK. Everything else goes through CDP directly.

## Known limits

* The renderer's Node integration is off (`require === undefined`), so file
  access goes through the preload bridge or through CDP, not `fs`.
* Angular runs in production mode (`window.ng` is absent); reach services via
  `__ngContext__` on app elements when you need them.
* Webpack module ids (`3071`, `3375`, `8299`) are build-specific — re-probe
  after an app upgrade instead of hard-coding them.
