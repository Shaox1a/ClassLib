(() => {
  const form = document.querySelector('[data-direct-upload]');
  if (!form) return;
  const status = form.querySelector('[data-upload-status]');
  const button = form.querySelector('button[type=submit]');
  const csrf = form.querySelector('[name=csrfmiddlewaretoken]').value;
  let pending = null;
  form.querySelector('[type=file]').addEventListener('change', () => { pending = null; });

  async function post(action, values) {
    const response = await fetch(new URL(action + '/', window.location.href), {
      method: 'POST', credentials: 'same-origin',
      headers: {'X-CSRFToken': csrf}, body: new URLSearchParams(values),
    });
    if (response.redirected) throw new Error('登录已过期，请刷新页面后重新登录。');
    const result = await response.json();
    if (!response.ok) {
      if (response.status === 400) pending = null;
      throw new Error(result.error || '操作失败，请重试。');
    }
    return result;
  }

  form.addEventListener('submit', async event => {
    event.preventDefault();
    const file = form.querySelector('[type=file]').files[0];
    if (!file) return;
    button.disabled = true;
    try {
      if (!pending) {
        status.textContent = '正在上传，请保持页面打开…';
        const upload = await post('begin', {name: file.name, size: file.size});
        const response = await fetch(upload.url, {
          method: 'PUT', headers: {'Content-Type': 'application/octet-stream'}, body: file,
        });
        if (!response.ok) throw new Error('文件上传失败，请重试。');
        pending = upload.ticket;
      }
      status.textContent = '上传完成，正在校验文件…';
      const result = await post('finish', {ticket: pending});
      window.location.assign(result.redirect);
    } catch (error) {
      status.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
})();
