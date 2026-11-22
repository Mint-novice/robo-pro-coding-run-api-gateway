// 批量导出全部块定义（type / 标题 / 输入 / 字段 / 生成代码）到 JSON
// 用法：node dumpblocks.js <out.json> [port]
const fs = require('fs');
const PORT = process.env.CDP_PORT || process.argv[3] || 9334;
const OUT = process.argv[2] || 'block-schema.json';
const PROBE = fs.readFileSync(__dirname + '/probe5.js', 'utf8');
const BATCH = 40;

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
        setTimeout(() => {
          if (pending.has(mid)) { pending.delete(mid); reject(new Error('timeout ' + method)); }
        }, 90000);
      });
    }
  });
}

(async () => {
  const target = (await listTargets()).filter((t) => t.type === 'page')[0];
  if (!target) throw new Error('no page target');
  const c = await connect(target.webSocketDebuggerUrl);

  const all = [];
  let total = null;
  for (let start = 0; total === null || start < total; start += BATCH) {
    const expr = `(async () => { const __ARGV = ${JSON.stringify([String(start), String(BATCH)])}; ${PROBE} })()`;
    const r = await c.send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails).slice(0, 400));
    const v = r.result.value;
    if (!v) break;
    total = v.total;
    all.push(...v.data);
    process.stderr.write(`\r${all.length}/${total}`);
  }
  c.close();

  const payload = {
    source: 'ROBO Pro Coding in-process Blockly registry',
    generatedAt: new Date().toISOString(),
    total: all.length,
    blocks: all,
  };
  fs.writeFileSync(OUT, JSON.stringify(payload, null, 1), 'utf8');
  const withCode = all.filter((b) => b.code).length;
  console.log(`\nwrote ${OUT}: ${all.length} blocks, ${withCode} with generated code`);
})().catch((e) => { console.error('ERR', e.message); process.exit(1); });
