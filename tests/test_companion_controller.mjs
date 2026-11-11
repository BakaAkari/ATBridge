import assert from 'node:assert/strict';

const elements = Object.fromEntries(['status', 'connect', 'disconnect', 'token', 'fab', 'pair', 'pair-code'].map(id => [id, {
  id, textContent: '', value: '', disabled: id === 'disconnect', handlers: {},
  addEventListener(type, callback) { this.handlers[type] = callback; }
}]));
globalThis.document = {getElementById: id => elements[id]};
const windowHandlers = {};
globalThis.window = {addEventListener: (type, callback) => { windowHandlers[type] = callback; }};

const jobs = [];
const fetchCalls = [];
const pairTickets = [];
const pairCancels = [];
let injectionResult;
let downloadOptions;
let downloadId = 70;
let searchResult = {state: 'complete', exists: true, fileSize: 42, filename: '/downloads/ATBridge/job/rock.zip'};
let beginDownload;
const cancelled = [];
const pendingTimers = [];
let stallNextPoll = false;
let stalledPoll;
let pairState = 'approved';
let pairRequestNumber = 0;
let stallPairStatus = false;
let stalledPairStatus;
let delayNextPairCancel = false;
let pendingPairCancel;
globalThis.chrome = {
  tabs: {
    query: async () => [{id: 1, active: true}],
    create: async () => {}
  },
  scripting: {executeScript: async () => [{result: injectionResult}]},
  downloads: {
    download: options => {
      downloadOptions = options;
      if (beginDownload) return new Promise(resolve => { beginDownload = () => resolve(downloadId); });
      return Promise.resolve(downloadId);
    },
    search: async () => [searchResult],
    cancel: async id => { cancelled.push(id); }
  }
};

const response = body => ({ok: true, json: async () => body});
globalThis.fetch = async (url, options) => {
  fetchCalls.push({url, options, body: options.body && JSON.parse(options.body)});
  if (url.endsWith('/pair/request')) {
    const ticket = `ticket-${++pairRequestNumber}`;
    pairTickets.push(ticket);
    return response({state: 'pending', code: '123456', ticket});
  }
  if (url.endsWith('/pair/cancel')) {
    pairCancels.push(options.body && JSON.parse(options.body));
    if (delayNextPairCancel) {
      delayNextPairCancel = false;
      return new Promise(resolve => { pendingPairCancel = {resolve}; });
    }
    return response({state: 'cancelled'});
  }
  if (url.endsWith('/pair/status')) {
    if (stallPairStatus) {
      stallPairStatus = false;
      return new Promise(resolve => { stalledPairStatus = {resolve, signal: options.signal}; });
    }
    return response({state: pairState, token: 'd'.repeat(64)});
  }
  if (url.endsWith('/hello')) return response({ok: true});
  if (url.endsWith('/poll')) {
    if (stallNextPoll) {
      stallNextPoll = false;
      return new Promise((resolve, reject) => { stalledPoll = {resolve, reject, signal: options.signal}; });
    }
    return response(jobs.shift() || {job: null, active: []});
  }
  if (url.endsWith('/result')) return response({ok: true});
  throw new Error(`Unexpected bridge request: ${url}`);
};

const realSetTimeout = globalThis.setTimeout;
const realClearTimeout = globalThis.clearTimeout;
globalThis.setTimeout = (callback, delay) => {
  if (delay === 500) return setImmediate(callback);
  const timer = {callback, delay};
  if (delay === 1000) pendingTimers.push(timer);
  return timer;
};
globalThis.clearTimeout = timer => {
  const index = pendingTimers.indexOf(timer);
  if (index !== -1) pendingTimers.splice(index, 1);
};
await import('../companion/extension/connect.mjs');

const flush = () => new Promise(resolve => setImmediate(resolve));
async function until(predicate, description) {
  for (let i = 0; i < 100; i++) {
    if (predicate()) return;
    await flush();
  }
  assert.fail(`Timed out waiting for ${description}; status=${elements.status.textContent}; calls=${fetchCalls.map(call => call.url).join(',')}`);
}
const click = id => elements[id].handlers.click();
const job = (id, action, params = {}) => ({job: {id, action, params}, active: [id]});

try {
  elements.token.value = 'a'.repeat(64);
  jobs.push(job('search-1', 'search', {query: 'rock'}));
  injectionResult = {ok: true, data: {items: [{uid: 'asset-1'}], cursor: 'next'}};
  await click('connect');
  assert.equal(elements.token.value, '');
  assert.equal(fetchCalls.find(call => call.url.endsWith('/hello')).options.headers.Authorization,
    `Bearer ${'a'.repeat(64)}`);
  await until(() => fetchCalls.some(call => call.body?.id === 'search-1'), 'search result handoff');
  assert.deepEqual(fetchCalls.find(call => call.body?.id === 'search-1').body.data, injectionResult.data);
  assert.equal(elements.status.textContent, '请求完成，可继续在 Blender 操作。');

  jobs.push(job('download-1', 'download', {name: 'rock.zip'}));
  injectionResult = {ok: true, data: {url: 'https://download.example/rock.zip', name: 'rock.zip', size: 42}};
  await until(() => pendingTimers.length > 0, 'scheduled poll after search');
  pendingTimers.shift().callback();
  await until(() => fetchCalls.some(call => call.body?.id === 'download-1'), 'download file handoff');
  assert.deepEqual(fetchCalls.find(call => call.body?.id === 'download-1').body.data,
    {path: '/downloads/ATBridge/job/rock.zip'});
  assert.equal(downloadOptions.filename, 'ATBridge/download-1/rock.zip');
  assert.equal(elements.status.textContent, '下载已交给 Blender 校验；完成后可在 Blender 导入。');

  jobs.push(job('download-cancel', 'download', {name: 'rock.zip'}));
  injectionResult = {ok: true, data: {url: 'https://download.example/rock.zip', name: 'rock.zip', size: 42}};
  downloadOptions = undefined;
  await until(() => pendingTimers.length > 0, 'scheduled poll');
  beginDownload = true;
  pendingTimers.shift().callback();
  await until(() => downloadOptions?.filename === 'ATBridge/download-cancel/rock.zip', 'download creation');
  await click('disconnect');
  assert.equal(elements.status.textContent, '已断开；如有未完成任务，请在 Blender 取消。');
  beginDownload();
  beginDownload = null;
  await until(() => cancelled.includes(downloadId), 'late download cancellation');
  assert.equal(fetchCalls.some(call => call.body?.id === 'download-cancel' && call.body.data), false);

  elements.token.value = 'b'.repeat(64);
  jobs.push(job('auth-expired', 'search', {query: 'metal'}));
  injectionResult = {ok: false, error: 'AUTH_REQUIRED'};
  await click('connect');
  await until(() => fetchCalls.some(call => call.body?.id === 'auth-expired'), 'auth error handoff');
  assert.equal(fetchCalls.find(call => call.body?.id === 'auth-expired').body.error, 'AUTH_REQUIRED');
  const expiredMessage = 'Fab 登录已过期，请在官方页面重新登录，再从 Blender 重试。';
  assert.equal(elements.status.textContent, expiredMessage);
  assert.equal(downloadOptions.saveAs, false);

  await until(() => pendingTimers.length > 0, 'poll timer before stale poll');
  stallNextPoll = true;
  pendingTimers.shift().callback();
  await until(() => stalledPoll, 'pending old poll');
  await click('disconnect');
  assert.equal(stalledPoll.signal.aborted, true);
  elements.token.value = 'c'.repeat(64);
  jobs.push(job('new-session', 'search', {query: 'wood'}));
  injectionResult = {ok: false, error: 'AUTH_REQUIRED'};
  await click('connect');
  await until(() => fetchCalls.some(call => call.body?.id === 'new-session'), 'new session response');
  assert.equal(elements.status.textContent, expiredMessage);
  stalledPoll.reject(new Error('old poll failed after reconnect'));
  await flush();
  assert.equal(elements.status.textContent, expiredMessage);
  assert.equal(elements.disconnect.disabled, false);
  await click('disconnect');
  await click('pair');
  assert.equal(elements.disconnect.disabled, false);
  assert.equal(elements.status.textContent, '已连接。在 Blender 搜索资产。');
  assert.equal(fetchCalls.filter(call => call.url.endsWith('/hello')).at(-1).options.headers.Authorization,
    'Bearer ' + 'd'.repeat(64));
  await click('disconnect');
  pairState = 'denied';
  await click('pair');
  assert.equal(elements.status.textContent, 'Blender 已拒绝连接。');
  assert.equal(elements.pair.disabled, false);
  pairState = 'expired';
  await click('pair');
  assert.equal(elements.status.textContent, '配对已过期，请在 Blender 重新开启配对。');

  const helloCount = fetchCalls.filter(call => call.url.endsWith('/hello')).length;
  const cancellationBaseline = pairCancels.length;
  stallPairStatus = true;
  void click('pair');
  await until(() => stalledPairStatus, 'pending pairing status request');
  delayNextPairCancel = true;
  const stopPromise = click('disconnect');
  await until(() => pendingPairCancel, 'deferred pairing cancellation');
  assert.equal(elements.connect.disabled, true);
  assert.equal(elements.pair.disabled, true);
  assert.equal(elements.disconnect.disabled, true);
  pendingPairCancel.resolve(response({state: 'cancelled'}));
  await stopPromise;
  assert.equal(elements.connect.disabled, false);
  assert.equal(elements.pair.disabled, false);
  await until(() => pairCancels.length === cancellationBaseline + 1, 'pair cancellation after disconnect');
  assert.equal(pairCancels.at(-1).ticket, pairTickets.at(-1));
  assert.equal(stalledPairStatus.signal.aborted, true);
  stalledPairStatus.resolve(response({state: 'approved', token: 'e'.repeat(64)}));
  await flush();
  assert.equal(fetchCalls.filter(call => call.url.endsWith('/hello')).length, helloCount,
    'an approval arriving after disconnect must not connect');
  assert.equal(elements.disconnect.disabled, true);

  pairState = 'pending';
  stalledPairStatus = null;
  stallPairStatus = true;
  void click('pair');
  await until(() => stalledPairStatus, 'retry pairing status request');
  const retryTicket = pairTickets.at(-1);
  await click('disconnect');
  await until(() => pairCancels.length === cancellationBaseline + 2, 'retry ticket cancellation');
  assert.equal(pairCancels.at(-1).ticket, retryTicket);
  assert.notEqual(pairCancels.at(-1).ticket, pairCancels.at(-2).ticket,
    'retry cancellation must target its own ticket, not the previous request');
  console.log('PASS: pairing approval/denial/expiry/cancel, search/download handoffs, auth expiry, and stale async isolation');
} finally {
  globalThis.setTimeout = realSetTimeout;
  globalThis.clearTimeout = realClearTimeout;
}
