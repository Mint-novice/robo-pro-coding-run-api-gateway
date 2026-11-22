// 把本地文件塞进页面的 <input type=file>（绕过系统文件对话框）
// 用法：node setfile.js <file path...>
const PORT = process.env.CDP_PORT || 9334;
const files = process.argv.slice(2);

async function targets() {
  const r = await fetch(`http://127.0.0.1:${PORT}/json/list`);
  return r.json();
}
function connect(u) {
  return new Promise((res, rej) => {
    const ws = new WebSocket(u);
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
        setTimeout(() => { if (pending.has(mid)) { pending.delete(mid); reject(new Error('timeout ' + method)); } }, 30000);
      });
    }
  });
}

(async () => {
  const t = (await targets()).filter((v) => v.type === 'page')[0];
  const c = await connect(t.webSocketDebuggerUrl);
  await c.send('DOM.enable');
  const doc = await c.send('DOM.getDocument', { depth: -1, pierce: true });
  const q = await c.send('DOM.querySelector', { nodeId: doc.root.nodeId, selector: 'input[type=file]' });
  if (!q.nodeId) throw new Error('no file input on page');
  await c.send('DOM.setFileInputFiles', { nodeId: q.nodeId, files });
  console.log('set files:', files);
  c.close();
})().catch((e) => { console.error('ERR', e.message); process.exit(1); });
