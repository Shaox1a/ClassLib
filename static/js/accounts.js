(() => {
    const form = document.querySelector('[data-account-selection]');
    if (!form) return;
    const all = form.querySelector('[data-select-all]');
    const boxes = [...form.querySelectorAll('input[name="selected"]')];
    const count = form.querySelector('[data-selection-count]');
    const submit = form.querySelector('[data-bulk-submit]');
    const action = form.elements.action;
    const group = form.elements.permission_group;
    const update = () => {
        const selected = boxes.filter(box => box.checked).length;
        count.textContent = `已选 ${selected} 个`;
        all.checked = boxes.length > 0 && selected === boxes.length;
        all.indeterminate = selected > 0 && selected < boxes.length;
        submit.disabled = selected === 0;
        group.hidden = action.value !== 'move';
        group.disabled = action.value !== 'move';
        group.required = action.value === 'move';
    };
    all.addEventListener('change', () => {
        boxes.forEach(box => { box.checked = all.checked; });
        update();
    });
    boxes.forEach(box => box.addEventListener('change', update));
    action.addEventListener('change', update);
    update();
})();
