// Search and filters for the card pages (tasks.html, datasets.html, models.html).
//
//   Catalog.init({
//     grid: document.getElementById('taskGrid'), cards: '.task-card',
//     count: document.getElementById('visibleCount'),
//     search: document.getElementById('catalogSearch'),
//     empty: document.getElementById('catalogEmpty'),
//     facets: [
//       // Buttons read the card's data-type; a card may list several values,
//       // space-separated (data-modality="ehr image").
//       { key: 'type', attr: 'type', el: ..., options: [['binary', 'Binary'], ...] },
//       // A select suits facets with many values, such as datasets.
//       { key: 'dataset', attr: 'datasets', el: ..., kind: 'select', all: 'All datasets', options: [...] },
//     ],
//   });
//
// Search matches every word against the card's text. The search and each
// facet live in the URL (tasks.html?dataset=MIMIC3Dataset&q=mortality), so a
// filtered view can be shared or linked to. Counts show how many cards each
// option would leave, given the search and the other facets.
const Catalog = (() => {
  // Datasets whose page also lists the tasks of related classes (kept in step
  // with docs/extensions/dataset_tasks.py in PyHealth). Filtering tasks by
  // MIMIC4Dataset includes those that cite MIMIC4EHRDataset.
  const RELATED = {
    MIMIC4Dataset: ['MIMIC4EHRDataset', 'MIMIC4NoteDataset', 'MIMIC4CXRDataset', 'MIMIC4EDDataset'],
    MSDHippocampusDataset: ['MSDSegmentationDataset'],
    MSDProstateDataset: ['MSDSegmentationDataset'],
    MSDSpleenDataset: ['MSDSegmentationDataset'],
  };

  // The datasets whose task lists include a task citing cls, cls first.
  function withRelated(cls) {
    return [cls, ...Object.keys(RELATED).filter(parent => RELATED[parent].includes(cls))];
  }

  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  function init({ grid, cards: selector, count, search, empty, facets }) {
    const cards = [...grid.querySelectorAll(selector)].map(el => ({
      el,
      text: `${el.id} ${el.textContent}`.toLowerCase().replace(/\s+/g, ' '),
      values: Object.fromEntries(facets.map(f =>
        [f.key, (el.dataset[f.attr] || '').split(' ').filter(Boolean)])),
    }));

    const params = new URLSearchParams(location.search);
    const state = { q: params.get('q') || '' };
    facets.forEach(f => {
      // Offer only options some card has, in the given order.
      f.options = f.options.filter(([value]) => cards.some(c => c.values[f.key].includes(value)));
      const wanted = params.get(f.key);
      state[f.key] = f.options.some(([value]) => value === wanted) ? wanted : 'all';
    });
    if (search) search.value = state.q;

    const words = () => state.q.toLowerCase().split(/\s+/).filter(Boolean);
    const matches = (card, skip) => words().every(w => card.text.includes(w)) &&
      facets.every(f => f.key === skip || state[f.key] === 'all' || card.values[f.key].includes(state[f.key]));

    function render() {
      let shown = 0;
      cards.forEach(card => {
        const show = matches(card);
        card.el.style.display = show ? '' : 'none';
        if (show) shown++;
      });
      if (count) count.textContent = shown;
      if (empty) empty.hidden = shown > 0;

      // Each option's count: the cards it would leave, other filters kept.
      facets.forEach(f => {
        const pool = cards.filter(card => matches(card, f.key));
        const n = value => value === 'all' ? pool.length
          : pool.filter(card => card.values[f.key].includes(value)).length;
        if (f.kind === 'select') {
          f.el.innerHTML = [['all', f.all || 'All'], ...f.options].map(([value, label]) =>
            `<option value="${esc(value)}"${value === state[f.key] ? ' selected' : ''}>${esc(label)} (${n(value)})</option>`).join('');
        } else {
          // Rebuilding the buttons drops focus; give it back for keyboard users.
          const focused = f.el.contains(document.activeElement) && document.activeElement.dataset.value;
          f.el.innerHTML = [['all', 'All'], ...f.options].map(([value, label]) => {
            const k = n(value), active = value === state[f.key];
            return `<button type="button" class="filter-btn${active ? ' active' : ''}" data-value="${esc(value)}"` +
              ` aria-pressed="${active}"${k || active ? '' : ' disabled'}>${esc(label)} <span style="opacity:0.65;">(${k})</span></button>`;
          }).join('');
          if (focused) f.el.querySelector(`[data-value="${CSS.escape(focused)}"]`)?.focus();
        }
      });

      const url = new URLSearchParams();
      if (state.q) url.set('q', state.q);
      facets.forEach(f => { if (state[f.key] !== 'all') url.set(f.key, state[f.key]); });
      const query = url.toString();
      history.replaceState(null, '', `${location.pathname}${query ? `?${query}` : ''}${location.hash}`);
    }

    facets.forEach(f => {
      if (f.kind === 'select') {
        f.el.addEventListener('change', () => { state[f.key] = f.el.value; render(); });
      } else {
        f.el.addEventListener('click', e => {
          const btn = e.target.closest('.filter-btn');
          if (!btn || btn.disabled) return;
          state[f.key] = btn.dataset.value;
          render();
        });
      }
    });

    if (search) {
      search.addEventListener('input', () => { state.q = search.value.trim(); render(); });
      search.addEventListener('keydown', e => {
        if (e.key === 'Escape') { search.value = ''; state.q = ''; render(); }
      });
      // "/" jumps to the search box, as on GitHub and the docs.
      document.addEventListener('keydown', e => {
        if (e.key === '/' && !/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName)) {
          e.preventDefault();
          search.focus();
        }
      });
    }

    if (empty) {
      empty.addEventListener('click', e => {
        if (!e.target.closest('[data-clear]')) return;
        state.q = '';
        if (search) search.value = '';
        facets.forEach(f => { state[f.key] = 'all'; });
        render();
      });
    }

    render();
  }

  return { init, esc, withRelated, RELATED };
})();
