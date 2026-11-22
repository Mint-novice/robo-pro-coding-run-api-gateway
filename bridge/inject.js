// 把本地 JS 文件注入渲染进程执行（避免命令行转义问题）
// 用法：node inject.js <script.js>
const PORT = process.env.CDP_PORT || 9333;
const fs = require('fs');

async function targets() {
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
        }, 60000);
      });
    }
  });
}

(async () => {
  const file = process.argv[2];
  const argv = process.argv.slice(3);
  const code = fs.readFileSync(file, 'utf8');
  const t = (await targets()).filter((x) => x.type === 'page');
  if (!t.length) throw new Error('no page target');
  const c = await connect(t[0].webSocketDebuggerUrl);
  const r = await c.send('Runtime.evaluate', {
    expression: `(async () => { const __ARGV = ${JSON.stringify(argv)}; ${code} })()`,
    returnByValue: true,
    awaitPromise: true,
    userGesture: true,
  });
  if (r.exceptionDetails) {
    console.log('EXCEPTION:', JSON.stringify(r.exceptionDetails.exception || r.exceptionDetails, null, 2));
  } else {
    console.log(JSON.stringify(r.result.value, null, 2));
  }
  c.close();
})().catch((e) => { console.error('ERR', e.message); process.exit(1); });
