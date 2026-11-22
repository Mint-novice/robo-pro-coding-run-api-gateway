// 枚举块定义：每块的输入、字段、人话标题、以及生成代码
// 用法：node inject.js probe5.js <start> <count>
const req = (() => {
  let r;
  window.webpackChunkangular_electron.push([[Symbol()], {}, (x) => { r = x; }]);
  return r;
})();

const B = req(3375);
const PG = req(8299).pythonGenerator;
const start = Number(__ARGV[0] || 0);
const count = Number(__ARGV[1] || 80);

const types = Object.keys(B.Blocks || {});
const slice = types.slice(start, start + count);
const ws = new B.Workspace();
// 让生成器就绪（否则 definitions_ 未初始化会抛 import_* 错误）
try { PG.init(ws); } catch (e) {
  try { PG.definitions_ = {}; PG.functionNames_ = {}; PG.nameDB_ = null; } catch (_) {}
}
const out = [];

for (const t of slice) {
  const rec = { type: t };
  try {
    const blk = ws.newBlock(t);
    try { rec.title = blk.toString().replace(/\s+/g, ' ').slice(0, 100); } catch (e) { rec.title = ''; }
    rec.inputs = (blk.inputList || []).map((i) => ({
      name: i.name,
      type: i.type,
      check: i.connection && i.connection.getCheck ? i.connection.getCheck() : null,
    }));
    const fields = [];
    (blk.inputList || []).forEach((i) =>
      (i.fieldRow || []).forEach((f) => {
        let v = '';
        try { v = String(f.getValue()); } catch (e) { v = ''; }
        fields.push({ name: f.name, cls: (f.constructor && f.constructor.name) || '', value: v.slice(0, 40) });
      })
    );
    rec.fields = fields;
    try {
      const code = PG.blockToCode(blk);
      rec.code = Array.isArray(code) ? code[0] : code;
    } catch (e) {
      rec.codeErr = String((e && e.message) || e).slice(0, 80);
    }
    blk.dispose(false);
  } catch (e) {
    rec.err = String((e && e.message) || e).slice(0, 120);
  }
  out.push(rec);
}
ws.dispose();
return { total: types.length, start, count: out.length, data: out };
