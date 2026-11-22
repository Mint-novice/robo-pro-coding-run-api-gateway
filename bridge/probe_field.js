// 精确检查电机块的下拉选项与当前值
const req = (() => {
  let r;
  window.webpackChunkangular_electron.push([[Symbol()], {}, (x) => { r = x; }]);
  return r;
})();
const B = req(3375);
const out = { found: [] };

for (const ws of B.Workspace.getAll ? B.Workspace.getAll() : []) {
  for (const b of ws.getAllBlocks(false)) {
    if (b.type !== 'motor_set_speed') continue;
    const rows = [];
    (b.inputList || []).forEach((i) =>
      (i.fieldRow || []).forEach((f) => {
        let opts = null;
        try { opts = f.getOptions ? f.getOptions(false).map((o) => o[0] + '=' + o[1]) : null; } catch (e) {}
        rows.push({ name: f.name, value: String(f.getValue()), cls: f.constructor.name, opts });
      })
    );
    out.found.push({ wsId: ws.id, fields: rows, text: b.toString().slice(0, 120) });
  }
}
return out;
