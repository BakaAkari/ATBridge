import {fabRequest} from './fab-client.mjs';
const el = id => document.getElementById(id);
const base = 'http://127.0.0.1:28481';
const requests = new Set();
let pairingTicket = '';
let token = '', generation = 0, timer = null, busy = null;
const labels = {
  AUTH_REQUIRED: 'Fab 登录已过期，请在官方页面重新登录，再从 Blender 重试。',
  ACCESS_DENIED: 'Fab 拒绝访问。请打开官方页面检查登录或验证要求，再手动重试。',
  NOT_OWNED: '账户未拥有此资产，请在官方页面处理。',
  NO_FAB_TAB: '请打开并登录 Fab，再从 Blender 重试。',
  EXPIRED_URL: '下载链接已过期，请从 Blender 重新下载。'
};
function status(text) { el('status').textContent = text; }
async function send(route, body = {}, timeoutMs = 20000) {
  const controller = new AbortController();
  requests.add(controller);
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  let r;
  try { r = await fetch(base + route, {method: 'POST', headers: {'Content-Type': 'application/json',
    Authorization: 'Bearer ' + token}, body: JSON.stringify(body), signal: controller.signal}); }
  finally { clearTimeout(timeout); requests.delete(controller); }
  if (!r.ok) throw new Error('BRIDGE_REJECTED');
  return r.json();
}
async function stop() {
  const stopped = ++generation;
  for (const request of requests) request.abort();
  requests.clear();
  const ticket = pairingTicket;
  pairingTicket = '';
  clearTimeout(timer);
  const id = busy?.downloadId ?? null;
  if (id !== null) void chrome.downloads.cancel(id).catch(() => {});
  token = '';
  busy = null;
  el('disconnect').disabled = true;
  if (ticket) await send('/pair/cancel', {ticket}, 2000).catch(() => {});
  if (stopped !== generation) return stopped;
  el('connect').disabled = false;
  el('pair').disabled = false;
  el('pair-code').textContent = '';
  el('disconnect').disabled = true;
  status('已断开；如有未完成任务，请在 Blender 取消。');
  return stopped;
}
async function download(data, job, epoch, work) {
  const id = await chrome.downloads.download({url: data.url,
    filename: 'ATBridge/' + job.id + '/' + data.name, conflictAction: 'uniquify', saveAs: false});
  if (epoch !== generation || busy !== work) {
    await chrome.downloads.cancel(id).catch(() => {});
    throw new Error('CANCELLED');
  }
  work.downloadId = id;
  const started = Date.now();
  while (epoch === generation && busy === work && Date.now() - started < 14 * 60 * 1000) {
    const [item] = await chrome.downloads.search({id});
    if (!item || item.state === 'interrupted') throw new Error('DOWNLOAD_FAILED');
    if (item.state === 'complete') {
      work.downloadId = null;
      if (!item.exists || item.fileSize !== data.size) throw new Error('DOWNLOAD_FAILED');
      return {path: item.filename};
    }
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  await chrome.downloads.cancel(id).catch(() => {});
  throw new Error('CANCELLED');
}
async function execute(job, epoch, work) {
  try {
    const tabs = await chrome.tabs.query({url: 'https://www.fab.com/*'});
    if (!tabs.length) throw new Error('NO_FAB_TAB');
    const tab = tabs.find(t => t.active) || tabs[0];
    const [injection] = await chrome.scripting.executeScript({target: {tabId: tab.id},
      world: 'ISOLATED', func: fabRequest, args: [job]});
    if (epoch !== generation || busy !== work) return;
    const result = injection.result;
    if (!result?.ok) {
      const error = new Error(result?.error || 'NETWORK_ERROR');
      error.detail = result?.detail || '';
      throw error;
    }
    const data = job.action === 'download' ? await download(result.data, job, epoch, work) : result.data;
    if (epoch !== generation || busy !== work) return;
    await send('/result', {id: job.id, data});
    status(job.action === 'download' ? '下载已交给 Blender 校验；完成后可在 Blender 导入。' : '请求完成，可继续在 Blender 操作。');
  } catch (error) {
    if (epoch !== generation || busy !== work) return;
    const code = error.message;
    status(labels[code] || '任务失败：' + (code === 'BRIDGE_REJECTED' ? '文件交接或配对被拒绝，请检查下载目录。' : code));
    if (error.detail) status(el('status').textContent + '\n' + error.detail);
    await send('/result', {id: job.id, error: code}).catch(() => {});
  } finally {
    if (epoch === generation && busy === work) busy = null;
  }
}
async function poll(epoch) {
  if (epoch !== generation) return;
  try {
    const result = await send('/poll');
    if (epoch !== generation) return;
    if (busy && !result.active.includes(busy.id)) {
      const cancelled = busy;
      busy = null;
      if (cancelled.downloadId !== null) await chrome.downloads.cancel(cancelled.downloadId).catch(() => {});
      status('任务已取消。');
    }
    if (result.job && !busy) {
      busy = {id: result.job.id, downloadId: null};
      status('正在处理：' + result.job.action);
      void execute(result.job, epoch, busy);
    }
    timer = setTimeout(() => poll(epoch), 1000);
  } catch {
    if (epoch !== generation) return;
    const stopped = await stop();
    if (stopped === generation) status('Blender 连接断开。请检查服务并重新配对。');
  }
}
async function connected(epoch) {
  await send('/hello');
  if (epoch !== generation) return;
  el('token').value = '';
  el('pair-code').textContent = '';
  el('disconnect').disabled = false;
  status('已连接。在 Blender 搜索资产。');
  void poll(epoch);
}
function beginConnect() {
  const epoch = ++generation;
  el('connect').disabled = true;
  el('pair').disabled = true;
  el('disconnect').disabled = false;
  return epoch;
}
async function connectFailed(epoch, message) {
  if (epoch !== generation) return;
  const stopped = await stop();
  if (stopped === generation) status(message);
}
el('connect').addEventListener('click', async () => {
  token = el('token').value.trim();
  if (!/^[a-f0-9]{64}$/.test(token)) return status('请粘贴 Blender 复制的完整配对码。');
  const epoch = beginConnect();
  try { await connected(epoch); }
  catch { await connectFailed(epoch, '无法连接。请启动 Blender 服务，核对配对码及端口。'); }
});
el('pair').addEventListener('click', async () => {
  token = '';
  const epoch = beginConnect();
  try {
    const request = await send('/pair/request');
    if (epoch !== generation) {
      if (request.ticket) void send('/pair/cancel', {ticket: request.ticket}, 2000).catch(() => {});
      return;
    }
    if (request.state !== 'pending') {
      return connectFailed(epoch, '请在 Blender 点击“重新配对”，再请求连接。');
    }
    pairingTicket = request.ticket;
    el('pair-code').textContent = '确认码：' + request.code;
    status('请核对 Blender 显示的确认码，并在那里点击“允许连接”。有效期最多 2 分钟。');
    const deadline = Date.now() + 120000;
    while (epoch === generation && Date.now() < deadline) {
      await new Promise(resolve => setTimeout(resolve, 500));
      if (epoch !== generation) return;
      const result = await send('/pair/status', {ticket: request.ticket});
      if (epoch !== generation) return;
      if (result.state === 'approved') {
        if (!/^[a-f0-9]{64}$/.test(result.token)) throw new Error('INVALID_TOKEN');
        pairingTicket = '';
        token = result.token;
        return await connected(epoch);
      }
      if (result.state !== 'pending') {
        return connectFailed(epoch, result.state === 'denied' ? 'Blender 已拒绝连接。' : '配对已过期，请在 Blender 重新开启配对。');
      }
    }
    await connectFailed(epoch, '配对已过期，请在 Blender 重新开启配对。');
  } catch {
    await connectFailed(epoch, '无法连接 Blender。请检查插件已启动、端口未占用，然后重试。');
  }
});
el('disconnect').addEventListener('click', stop);
el('fab').addEventListener('click', () => chrome.tabs.create({url: 'https://www.fab.com/'}));
window.addEventListener('beforeunload', () => {
  if (busy?.downloadId != null) void chrome.downloads.cancel(busy.downloadId);
});
