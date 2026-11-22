// 极简 CDP 客户端：连到 ROBO Pro Coding 的渲染进程，执行 JS / 截图
// 用法：
//   node cdp.js eval "<expression>"      -> 返回求值结果（JSON）
//   node cdp.js shot <out.png>           -> 保存截图
//   node cdp.js list                     -> 列出目标
const PORT = process.env.CDP_PORT || 9333;

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
    ws.addEventListener('error', (e) => rej(e));
    ws.addEventListener('message', (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) {
        const { resolve, reject } = pending.get(msg.id);
        pending.delete(msg.id);
        msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result);
      }
    });
    function send(method, params = {}) {
      const mid = ++id;
      return new Promise((resolve, reject) => {
        pending.set(mid, { resolve, reject });
        ws.send(JSON.stringify({ id: mid, method, params }));
        setTimeout(() => {
          if (pending.has(mid)) {
            pending.delete(mid);
            reject(new Error('timeout ' + method));
          }
        }, 30000);
      });
    }
  });
}

(async () => {
  const cmd = process.argv[2] || 'list';
  const t = (await targets()).filter((x) => x.type === 'page');
  if (cmd === 'list') {
    console.log(JSON.stringify(t.map((x) => ({ id: x.id, title: x.title, url: x.url })), null, 2));
    return;
  }
  if (!t.length) throw new Error('no page target');
  const c = await connect(t[0].webSocketDebuggerUrl);
  if (cmd === 'eval') {
    const expr = process.argv[3];
    const r = await c.send('Runtime.evaluate', {
      expression: expr,
      returnByValue: true,
      awaitPromise: true,
      userGesture: true,
    });
    if (r.exceptionDetails) {
      console.log('EXCEPTION:', JSON.stringify(r.exceptionDetails, null, 2));
    } else {
      console.log(JSON.stringify(r.result.value, null, 2));
    }
  } else if (cmd === 'shot') {
    const out = process.argv[3] || 'shot.png';
    const r = await c.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
    require('fs').writeFileSync(out, Buffer.from(r.data, 'base64'));
    console.log('saved', out);
  }
  c.close();
})().catch((e) => {
  console.error('ERR', e.message);
  process.exit(1);
});
