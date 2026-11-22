// 读取应用里“真实打开的工作区”，并生成 Python（等价于点‘运行’时软件自己生成的代码）
const req = (() => {
  let r;
  window.webpackChunkangular_electron.push([[Symbol()], {}, (x) => { r = x; }]);
  return r;
})();
const B = req(3375);
const PG = req(8299).pythonGenerator;

const out = { workspaces: [] };
const all = B.Workspace.getAll ? B.Workspace.getAll() : [];
out.count = all.length;

for (const ws of all) {
  const blocks = ws.getAllBlocks(false);
  if (!blocks.length) continue;
  const types = blocks.map((b) => b.type);
  const rec = {
    types: types.slice(0, 12),
    blockCount: types.length,
    hasStart: types.includes('start_block'),
  };
  const motor = blocks.find((b) => b.type === 'motor_set_speed');
  if (motor) {
    rec.motor = {
      instance: motor.getFieldValue('instance_name_0'),
      direction: motor.getFieldValue('direction_0'),
      speed: motor.getInputTargetBlock('speed') ? motor.getInputTargetBlock('speed').getFieldValue('NUM') : null,
    };
  }
  if (rec.hasStart) {
    try {
      PG.init(ws);
    } catch (e) {
      try { PG.definitions_ = {}; } catch (_) {}
    }
    try {
      rec.code = PG.workspaceToCode(ws);
    } catch (e) {
      rec.codeErr = String(e.message || e);
    }
  }
  out.workspaces.push(rec);
}
return out;
