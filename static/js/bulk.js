(() => {
  const toggle = document.getElementById('bulk-toggle');
  const form = document.getElementById('bulk-actions');
  const all = document.getElementById('bulk-all');
  const count = document.getElementById('bulk-count');
  const links = document.querySelectorAll('[data-bulk-kind]');
  const itemCount = new Set(Array.from(links, link => link.dataset.bulkKind + ':' + link.dataset.bulkId)).size;
  const selected = { folders: new Set(), files: new Set() };
  const labels = [];
  const boxes = [];

  function refresh() {
    const total = selected.folders.size + selected.files.size;
    for (const box of boxes) {
      box.checked = selected[box.dataset.kind].has(box.value);
    }
    all.checked = total > 0 && total === itemCount;
    all.indeterminate = total > 0 && !all.checked;
    count.textContent = `已选 ${total} 项`;
    form.querySelectorAll('button').forEach(button => { button.disabled = total === 0; });
    for (const [kind, ids] of Object.entries(selected)) {
      form.elements.namedItem(kind).value = [...ids].join(',');
    }
  }

  for (const link of links) {
    const label = document.createElement('label');
    label.className = link.className + ' bulk-item';
    label.hidden = true;
    const box = document.createElement('input');
    box.type = 'checkbox';
    box.dataset.kind = link.dataset.bulkKind;
    box.value = link.dataset.bulkId;
    label.append(box, ...Array.from(link.childNodes, node => node.cloneNode(true)));
    link.after(label);
    labels.push(label);
    boxes.push(box);
    box.addEventListener('change', () => {
      const ids = selected[box.dataset.kind];
      if (box.checked) ids.add(box.value);
      else ids.delete(box.value);
      refresh();
    });
  }
  toggle.hidden = false;
  toggle.addEventListener('click', () => {
    const active = form.hidden;
    form.hidden = !active;
    toggle.setAttribute('aria-expanded', String(active));
    toggle.textContent = active ? '取消多选' : '多选';
    toggle.parentElement.querySelectorAll('a').forEach(link => { link.hidden = active; });
    links.forEach(link => { link.hidden = active; });
    labels.forEach(label => { label.hidden = !active; });
    selected.folders.clear();
    selected.files.clear();
    refresh();
  });
  all.addEventListener('change', () => {
    for (const box of boxes) {
      const ids = selected[box.dataset.kind];
      if (all.checked) ids.add(box.value);
      else ids.delete(box.value);
    }
    refresh();
  });
})();
