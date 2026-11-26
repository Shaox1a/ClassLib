(() => {
  const grid = document.querySelector('[data-reorder-grid]');
  if (!grid) return;

  const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value
    || document.cookie.split(';').map(part => part.trim()).find(part => part.startsWith('csrftoken='))?.slice(10);

  const cardSelector = '.item-card-folder[data-folder-id]';
  const cards = () => [...grid.querySelectorAll(cardSelector)];

  const bulkOpen = () => {
    const bulk = document.getElementById('bulk-actions');
    return bulk && !bulk.hidden;
  };

  const saveOrder = () => {
    if (!csrf) return;
    const body = new FormData();
    body.append('parent', grid.dataset.reorderParent || '');
    body.append('folders', cards().map(card => card.dataset.folderId).join(','));
    fetch(grid.dataset.reorderUrl, {
      method: 'POST',
      body,
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': csrf, 'X-Reorder-Form': '1' },
    });
  };

  const placeCard = (card, clientX, clientY) => {
    const target = document.elementFromPoint(clientX, clientY)?.closest(cardSelector);
    if (!target || target === card || !grid.contains(target)) return;
    const rect = target.getBoundingClientRect();
    const midX = rect.left + rect.width / 2;
    const midY = rect.top + rect.height / 2;
  if (clientY < midY || (Math.abs(clientY - midY) < rect.height / 4 && clientX < midX)) {
      grid.insertBefore(card, target);
      return;
    }
    grid.insertBefore(card, target.nextElementSibling);
  };

  let active = null;
  let dragged = false;
  let startX = 0;
  let startY = 0;

  const finish = (card, event) => {
    card.classList.remove('is-dragging');
    if (active === card) active = null;
    if (dragged) {
      event.preventDefault();
      saveOrder();
    } else if (card.dataset.folderUrl) {
      window.location.assign(card.dataset.folderUrl);
    }
    dragged = false;
  };

  grid.addEventListener('pointerdown', event => {
    if (bulkOpen() || event.button !== 0) return;
    const card = event.target.closest(cardSelector);
    if (!card) return;
    active = card;
    dragged = false;
    startX = event.clientX;
    startY = event.clientY;
    card.classList.add('is-dragging');
    card.setPointerCapture(event.pointerId);
  });

  grid.addEventListener('pointermove', event => {
    if (!active || bulkOpen()) return;
    if (!dragged && Math.hypot(event.clientX - startX, event.clientY - startY) < 10) return;
    dragged = true;
    placeCard(active, event.clientX, event.clientY);
  });

  grid.addEventListener('pointerup', event => {
    const card = event.target.closest(cardSelector);
    if (!active || !card || card !== active) return;
    try { card.releasePointerCapture(event.pointerId); } catch (_) { /* already released */ }
    finish(card, event);
  });

  grid.addEventListener('pointercancel', event => {
    const card = active;
    if (!card) return;
    card.classList.remove('is-dragging');
    active = null;
    dragged = false;
  });
})();