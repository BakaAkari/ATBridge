// Self-contained so Chrome can inject this function in an isolated Fab context.
export async function fabRequest(job) {
  let detail = '';
  const fail = code => { throw new Error(code); };
  const uid = value => {
    if (!/^[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(value)) fail('UNSUPPORTED');
    return value;
  };
  const get = async path => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch('https://www.fab.com' + path, {
        credentials: 'include', headers: {Accept: 'application/json'},
        signal: controller.signal, redirect: 'follow'
      });
      if (response.status === 401 || new URL(response.url).hostname !== 'www.fab.com') fail('AUTH_REQUIRED');
      if (response.status === 403) fail('ACCESS_DENIED');
      if (response.status === 429) fail('RATE_LIMITED');
      if (!response.ok) fail('NETWORK_ERROR');
      if (!(response.headers.get('content-type') || '').includes('application/json')) fail('SCHEMA_CHANGED');
      return await response.json();
    } finally { clearTimeout(timer); }
  };
  try {
    const p = job.params;
    if (job.action === 'search') {
      if (typeof p.query !== 'string' || !p.query.trim() || p.query.length > 200) fail('UNSUPPORTED');
      const query = new URLSearchParams({q: p.query, count: '12'});
      if (p.cursor) query.set('cursor', String(p.cursor).slice(0, 1024));
      const result = await get('/i/listings/search?' + query);
      if (!Array.isArray(result.results)) fail('SCHEMA_CHANGED');
      return {ok: true, data: {items: result.results.slice(0, 12).map(x => ({uid: uid(x.uid), title: String(x.title).slice(0, 200)})),
        cursor: result.cursors?.next || ''}};
    }
    if (!['files', 'download'].includes(job.action)) fail('UNSUPPORTED');
    const listing = uid(p.listing);
    const state = await get('/i/users/me/listings-states/' + listing);
    if (typeof state.acquired !== 'boolean') fail('SCHEMA_CHANGED');
    if (!state.acquired) fail('NOT_OWNED');
    const result = await get('/i/listings/' + listing + '/asset-formats/fbx');
    if (!Array.isArray(result.files)) fail('SCHEMA_CHANGED');
    const files = result.files.filter(x => x.status === 'ready' && typeof x.name === 'string'
      && /^[^/\\:\x00-\x1f]{1,180}\.zip$/i.test(x.name) && Number.isSafeInteger(x.size)
      && x.size > 0 && x.size <= 1024 ** 3).map(x => ({uid: uid(x.uid), name: x.name, size: x.size}));
    if (job.action === 'files') return {ok: true, data: {owned: true, files}};
    const file = files.find(x => x.uid === p.file && x.name === p.name && x.size === p.size);
    if (!file) { detail = 'Selected file metadata changed'; fail('UNSUPPORTED'); }
    const infoPath = '/i/listings/' + listing + '/asset-formats/fbx/files/' + uid(p.file) + '/download-info';
    // Refresh once if the site supplies a link that has already expired.
    for (let attempt = 0; attempt < 2; attempt++) {
      const info = await get(infoPath);
      const item = info.downloadInfo?.find(x => x.type === 'binary');
      if (!item || typeof item.downloadUrl !== 'string') fail('SCHEMA_CHANGED');
      const url = new URL(item.downloadUrl);
      if (url.protocol !== 'https:' || url.hostname !== 'content-download-emp.distro.on.epicgames.com'
          || url.username || url.password || (url.port && url.port !== '443')) {
        detail = 'Download host: ' + url.hostname; fail('UNSUPPORTED');
      }
      const expires = Date.parse(item.expires);
      if (!Number.isFinite(expires)) fail('SCHEMA_CHANGED');
      if (expires <= Date.now() + 30000) continue;
      return {ok: true, data: {url: url.href, name: file.name, size: file.size}};
    }
    fail('EXPIRED_URL');
  } catch (error) {
    const known = ['AUTH_REQUIRED', 'ACCESS_DENIED', 'RATE_LIMITED', 'SCHEMA_CHANGED',
      'NOT_OWNED', 'UNSUPPORTED', 'EXPIRED_URL'];
    return {ok: false, error: known.includes(error.message) ? error.message : 'NETWORK_ERROR', detail};
  }
}
