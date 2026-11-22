(() => {
  const form = document.querySelector('[data-upload-queue]');
  if (!form) return;
  const input = form.querySelector('[type=file]');
  const button = form.querySelector('button[type=submit]');
  const status = form.querySelector('[data-upload-status]');
  const list = form.querySelector('[data-upload-items]');
  const csrf = form.querySelector('[name=csrfmiddlewaretoken]').value;
  let queue = [];
  input.addEventListener('change', () => {
    queue = Array.from(input.files, file => ({file, done: false, id: crypto.randomUUID()}));
    list.replaceChildren();
    queue.forEach(item => { item.row = document.createElement('li'); list.append(item.row); show(item, '等待上传'); });
  });
  function show(item, text) { item.row.textContent = `${item.file.name} (${item.file.size} 字节)：${text}`; }
  async function post(action, data, extra = {}) {
    const response = await fetch(new URL(action, form.action), {method: 'POST', body: data,
      credentials: 'same-origin', headers: {'X-CSRFToken': csrf, 'X-Upload-Queue': '1', ...extra}});
    if (response.redirected || response.status === 403) {
      const error = new Error('登录或权限已失效，请重新登录后重试。'); error.pause = true; throw error;
    }
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || '操作失败，请重试。');
    return result;
  }
  async function authorize(item) {
    const values = item.auth ? {ticket: item.auth.ticket} : {name: item.file.name, size: item.file.size};
    item.auth = await post('begin/', new URLSearchParams(values));
    return new URL(item.auth.url).searchParams.get('token');
  }
  async function tus(item, token) {
    const headers = {'Tus-Resumable': '1.0.0', 'x-signature': token};
    if (!item.location) {
      const metadata = {bucketName: item.auth.bucket, objectName: item.auth.key, contentType: 'application/octet-stream'};
      const response = await fetch(item.auth.endpoint, {method: 'POST', headers: {...headers,
        'Upload-Length': String(item.file.size),
        'Upload-Metadata': Object.entries(metadata).map(([k,v]) => `${k} ${btoa(v)}`).join(',') }});
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`存储平台拒绝上传 (${response.status})：${detail.slice(0,300)}`);
      }
      const location = response.headers.get('Location');
      if (!location) throw new Error('存储未返回上传地址。');
      item.location = new URL(location, item.auth.endpoint).href;
      if (new URL(item.location).origin !== new URL(item.auth.endpoint).origin) throw new Error('上传地址无效。');
    }
    const head = await fetch(item.location, {method: 'HEAD', headers});
    if (head.status === 404 || head.status === 410) { item.location = null; throw new Error('上传已过期，请点击重试。'); }
    if (!head.ok) throw new Error('无法恢复上传，请重试。');
    let offset = Number(head.headers.get('Upload-Offset'));
    if (!Number.isSafeInteger(offset) || offset < 0 || offset > item.file.size) throw new Error('上传进度无效。');
    while (offset < item.file.size) {
      const chunk = item.file.slice(offset, offset + 6 * 1024 * 1024);
      const response = await fetch(item.location, {method: 'PATCH', headers: {...headers,
        'Content-Type': 'application/offset+octet-stream', 'Upload-Offset': String(offset)}, body: chunk});
      if (!response.ok) throw new Error(`上传中断 (${response.status})，点击重试以恢复。`);
      const next = Number(response.headers.get('Upload-Offset'));
      if (!Number.isSafeInteger(next) || next <= offset || next > item.file.size) throw new Error('上传进度无效。');
      offset = next;
      show(item, `上传中 ${Math.round(offset / item.file.size * 100)}%`);
    }
  }
  async function upload(item) {
    if (form.dataset.cloud !== 'true') {
      const data = new FormData(); data.append('upload', item.file);
      await post('', data, {'X-Upload-Id': item.id}); return;
    }
    if (item.confirming) { await post('finish/', new URLSearchParams({ticket: item.auth.ticket})); return; }
    const token = await authorize(item);
    if (item.file.size > 6 * 1024 * 1024) await tus(item, token);
    else {
      const response = await fetch(item.auth.url, {method: 'PUT', headers: {'Content-Type': 'application/octet-stream'}, body: item.file});
      if (!response.ok && response.status !== 409 && response.status !== 400) throw new Error(`存储拒绝上传 (${response.status})，请重试。`);
    }
    item.confirming = true;
    show(item, '确认中');
    await post('finish/', new URLSearchParams({ticket: item.auth.ticket}));
  }
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!queue.length) return;
    button.disabled = input.disabled = true;
    try {
      for (const item of queue.filter(i => !i.done)) {
        show(item, '上传中');
        try { await upload(item); item.done = true; show(item, '成功'); }
        catch (error) { show(item, `失败：${error.message}`); if (error.pause) break; }
      }
      const success = queue.filter(i => i.done).length;
      status.textContent = `成功 ${success} 个，未完成 ${queue.length - success} 个。可返回文件夹，或重试未完成项。`;
      button.textContent = '重试未完成项';
    } finally { button.disabled = queue.every(i => i.done); input.disabled = false; }
  });
})();
