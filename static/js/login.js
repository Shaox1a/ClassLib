(() => {
  const form = document.querySelector('[data-login-form]');
  if (!form) return;
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const button = form.querySelector('button');
    const error = form.querySelector('[data-login-error]');
    button.disabled = true;
    error.hidden = true;
    try {
      const response = await fetch(form.action, {method: 'POST', body: new FormData(form),
        credentials: 'same-origin', headers: {'X-Login-Form': '1'}});
      if (response.status === 403) throw new Error('页面凭据已过期，请刷新后重试。');
      const result = await response.json();
      if (!response.ok) throw new Error(result.error);
      const passwordInput = form.querySelector('input[name="password"]');
      if (passwordInput) passwordInput.value = '';
      window.location.assign(result.redirect);
    } catch (exception) {
      error.textContent = exception.message || '网络错误，请重试。';
      error.hidden = false;
    } finally { button.disabled = false; }
  });
})();
