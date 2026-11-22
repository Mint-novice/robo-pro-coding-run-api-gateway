// 用软件自带 Blockly 解析真实工程文件里的 .blockly，输出块树
// 用法：node verify_in_app.js <ctrl.blockly> <main.blockly>
const fs = require('fs');
const PORT = process.env.CDP_PORT || 9334;
const ctrlXml = fs.readFileSync(process.argv[2], 'utf8');
const mainXml = fs.readFileSync(process.argv[3], 'utf8');

async function listTargets() {
  const r = await fetch(`http://127.0.0.1:${PORT}/json/list`);
  return r.json();
}
function connect(wsUrl) {
  return new Promise((res, rej) => {
    const ws = new WebSocket(wsUrl);
    let id = 0;
    const pending = new Map();
    ws.addEventListener('open', () => res({ send, close: () => ws.close() }));
    ws.addEventListener('error', rej);
    ws.addEventListener('message', (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id && pending.has(m.id)) {
        const { resolve, reject } = pending.get(m.id);
        pending.delete(m.id);
        m.error ? reject(new Error(JSON.stringify(m.error))) : resolve(m.result);
      }
    });
    function send(method, params = {}) {
      const mid = ++id;
      return new Promise((resolve, reject) => {
        pending.set(mid, { resolve, reject });
        ws.send(JSON.stringify({ id: mid, method, params }));
        setTimeout(() => { if (pending.has(mid)) { pending.delete(mid); reject(new Error('timeout')); } }, 60000);
      });
    }
  });
}

const body = `
const req = (() => { let r; window.webpackChunkangular_electron.push([[Symbol()], {}, (x) => { r = x; }]); return r; })();
const B = req(3375);
const PG = req(8299).pythonGenerator;
const parse = (xml) => {
  const ws = new B.Workspace();
  try { PG.init(ws); } catch (e) { try { PG.definitions_ = {}; } catch (_) {} }
  const r = {};
  try {
    B.Xml.domToWorkspace(B.utils.xml.textToDom(xml), ws);
    r.blocks = ws.getAllBlocks(false).map((b) => {
      const kids = [];
      (b.inputList || []).forEach((i) => { const t = b.getInputTargetBlock(i.name); if (t) kids.push(i.name + '->' + t.type); });
      const f = {};
      (b.inputList || []).forEach((i) => (i.fieldRow || []).forEach((x) => { if (x.name) f[x.name] = String(x.getValue()); }));
      return { type: b.type, kids, fields: f };
    });
    try { r.code = PG.workspaceToCode(ws); } catch (e) { r.codeErr = String(e.message || e); }
  } catch (e) { r.error = String(e.message || e); }
  ws.dispose();
  return r;
};
return { controller: parse(CTRL), main: parse(MAIN) };
`;

(async () => {
  const t = (await listTargets()).filter((x) => x.type === 'page')[0];
  const c = await connect(t.webSocketDebuggerUrl);
  const expr = `(async () => { const CTRL = ${JSON.stringify(ctrlXml)}; const MAIN = ${JSON.stringify(mainXml)}; ${body} })()`;
  const r = await c.send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) {
    console.log('EXCEPTION', JSON.stringify(r.exceptionDetails).slice(0, 500));
  } else {
    console.log(JSON.stringify(r.result.value, null, 1));
  }
  c.close();
})().catch((e) => { console.error('ERR', e.message); process.exit(1); });
