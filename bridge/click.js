// 真实鼠标点击（CDP Input 域），参数：x y
const PORT = process.env.CDP_PORT || 9334;
const x = Number(process.argv[2]);
const y = Number(process.argv[3]);

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
        setTimeout(() => { if (pending.has(mid)) { pending.delete(mid); reject(new Error('timeout')); } }, 20000);
      });
    }
  });
}

(async () => {
  const t = (await targets()).filter((v) => v.type === 'page')[0];
  const c = await connect(t.webSocketDebuggerUrl);
  for (const type of ['mouseMoved', 'mousePressed', 'mouseReleased']) {
    await c.send('Input.dispatchMouseEvent', {
      type, x, y, button: 'left', buttons: type === 'mousePressed' ? 1 : 0, clickCount: type === 'mouseMoved' ? 0 : 1,
    });
    await new Promise((r) => setTimeout(r, 120));
  }
  console.log('clicked', x, y);
  c.close();
})().catch((e) => { console.error('ERR', e.message); process.exit(1); });
