# Troubleshooting

Every item below is a failure that actually happened while building this
toolkit, with the fix that worked.

## The app exits immediately when started from a script

```
ROBO Pro Coding.exe: bad option: --remote-debugging-port=9334
SyntaxError: Invalid or unexpected token   at ... LED_M1.ft:1
```

**Cause:** `ELECTRON_RUN_AS_NODE=1` is set in the environment. Electron then runs
the binary as `node`, treating the first argument as a JS entry point.

**Fix:** clear the variable for the child process only:

```powershell
cmd /c "set ELECTRON_RUN_AS_NODE=&& start "" ""C:\path\ROBO Pro Coding.exe"" --remote-debugging-port=9334"
```

`bridge/launch.ps1` does this for you. Check with `$env:ELECTRON_RUN_AS_NODE`.

## A second instance starts and vanishes

The app holds a single-instance lock per `--user-data-dir`. Give the bridge its
own profile (`bridge/launch.ps1` defaults to `%TEMP%\ftg-bridge`). If a previous
bridge instance crashed, delete the profile's `lockfile` / `SingletonLock`.

## The infinite loop is empty in the UI, but the XML has children

**Cause:** `<statement name="statement">` inside `loop_endless`. The block only
accepts **`DO`**; Blockly discards unrecognised statement inputs without an
error message.

**Fix:** use `<statement name="DO">` (and `name="statement"` only for
`start_block`). `ftg verify` fails such a file:

```
[FAIL] Motor_Run.blockly: <block type="loop_endless"> statement input must be ['DO'],
       found "statement" — children would be dropped
```

## Motor block shows `-` and the code becomes `-.set_speed(...)`

**Cause:** `instance_name_0` does not match `<controller-id>-<pin-block-id>` of
the motor attached in `lib/controller.blockly`, so the dropdown validator falls
back to the first option.

**Fix:** copy the pair from the controller block, e.g.
`ctrl000000000001` + `pinMotor00000001` → `ctrl000000000001-pinMotor00000001`.
Both ids are arbitrary strings, but they must match exactly.

## The project opens with an old program

The app keeps the loaded project in memory; it does not watch the file. Close
the project tab (×) and reopen, or restart the app. The bridge version
(`bridge/setfile.js`) re-injects the file and always reads it fresh.

## “加载项目 → 下一步” does nothing

The step is a stepper: pick the **本地** card first (`getBoundingClientRect()`
tells you where it is), then “下一步”. After that the page holds a real
`<input type=file>` – feed it with `DOM.setFileInputFiles` instead of typing
into an OS dialog.

## `verify` complains about an unknown block type

The block was typed by hand and does not exist in ROBO Pro Coding 6.5.4. Compare against

```bash
ftg blocks <keyword>
```

or `src/ftgateway/data/block-catalog.json`. Note that pin hardware blocks (`motor`,
`mini_switch`, `led`, …) live in `hardware_types`, not `block_types`.

## The app was updated and everything broke

Webpack module ids and block titles are build-specific. Re-run:

```bash
node bridge/dumpblocks.js src/ftgateway/data/block-schema.json
```

and re-check `docs/blocks.md` before trusting hard-coded ids.

## `unsaved: true` in the metadata

Generated files set `unsaved: false`. If it is `true`, the app may treat the
project as having unsaved changes; `ftg verify` accepts either, but generation
never writes `true`.
