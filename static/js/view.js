(() => {
  function select(mode) {
    document.querySelectorAll('[data-icon-view]').forEach(el => { el.hidden = mode === 'details'; });
    document.querySelectorAll('[data-details-view]').forEach(el => { el.hidden = mode !== 'details'; });
    document.querySelectorAll('[data-view]').forEach(el => el.setAttribute('aria-pressed', String(el.dataset.view === mode)));
  }
  let mode = 'icons';
  try { mode = localStorage.getItem('classlib-view') || mode; } catch (_) { /* storage is optional */ }
  select(mode === 'details' ? 'details' : 'icons');
  document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => {
    select(button.dataset.view);
    try { localStorage.setItem('classlib-view', button.dataset.view); } catch (_) { /* storage is optional */ }
  }));
})();
