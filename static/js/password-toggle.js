(() => {
  const EYE = '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>';
  const EYE_OFF = '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3l18 18"/><path d="M10.6 10.6a2 2 0 0 0 2.8 2.8"/><path d="M9.9 4.2A10.8 10.8 0 0 1 12 4c6.5 0 10 7 10 7a18.5 18.5 0 0 1-4.1 5.2"/><path d="M6.1 6.1A18.5 18.5 0 0 0 2 12s3.5 7 10 7a10.7 10.7 0 0 0 5.3-1.4"/></svg>';

  const setVisible = (input, button, visible) => {
    input.type = visible ? 'text' : 'password';
    button.setAttribute('aria-pressed', visible ? 'true' : 'false');
    button.setAttribute('aria-label', visible ? '隐藏密码' : '显示密码');
    button.innerHTML = visible ? EYE_OFF : EYE;
  };

  const enhance = input => {
    if (!input || input.type !== 'password' || input.dataset.passwordToggle === '1') return;
    if (input.closest('.password-field')) return;
    input.dataset.passwordToggle = '1';
    const wrap = document.createElement('div');
    wrap.className = 'password-field';
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'password-toggle';
    setVisible(input, button, false);
    button.addEventListener('click', () => {
      setVisible(input, button, input.type === 'password');
    });
    wrap.appendChild(button);
  };

  let ready = false;
  const init = () => {
    if (ready) return;
    ready = true;
    document.querySelectorAll('input[type="password"]').forEach(enhance);
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();