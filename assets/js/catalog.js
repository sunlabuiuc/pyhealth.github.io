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
//     // Optional: a table view, one row per card. Each column's cell is
//     // built from the card element; columns with a key can be sorted, by
//     // sort(card) or else by the cell's text.
//     table: {
//       el: document.getElementById('catalogTable'), toggle: document.getElementById('viewToggle'),
//       columns: [{ key: 'name', label: 'Task', cell: card => ..., sort: card => ... }, ...],
//     },
//   });
//
// Search matches every word against the card's text. The search and each
// facet live in the URL (tasks.html?dataset=MIMIC3Dataset&q=mortality), so a
// filtered view can be shared or linked to. Counts show how many cards each
// option would leave, given the search and the other facets. The view
// (?view=table) and the table's sort (?sort=-tasks) are in the URL too.
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

  // Text links to put in a table cell, copied from the card's own links:
  // links(card, [['.docs-link', 'Docs'], ['.example-link', 'Example']]).
  function links(card, wanted) {
    return wanted.map(([selector, label]) => {
      const a = card.querySelector(selector);
      return a ? `<a href="${esc(a.getAttribute('href'))}"${a.target ? ` target="${esc(a.target)}" rel="noopener"` : ''}>${esc(label)}</a>` : '';
    }).filter(Boolean).join('');
  }

  // A table cell's name: links to the card (in the card view) and shows the
  // class name below the title when they differ.
  function name(card, title, cls) {
    return `<a href="#${esc(card.id)}" data-card="${esc(card.id)}" class="cell-name">${esc(title)}</a>` +
      (cls && cls !== title ? `<span class="cell-sub">${esc(cls)}</span>` : '');
  }

  function init({ grid, cards: selector, count, search, empty, facets, table }) {
    const cards = [...grid.querySelectorAll(selector)].map(el => ({
      el,
      text: `${el.id} ${el.textContent}`.toLowerCase().replace(/\s+/g, ' '),
      values: Object.fromEntries(facets.map(f =>
        [f.key, (el.dataset[f.attr] || '').split(' ').filter(Boolean)])),
    }));

    const params = new URLSearchParams(location.search);
    const state = { q: params.get('q') || '', view: 'cards', sort: params.get('sort') || '' };
    if (table) {
      // The URL wins; then a link to one card (#ClassName) shows the cards;
      // otherwise the view this visitor last picked.
      let saved = null;
      try { saved = localStorage.getItem('catalog-view'); } catch (e) { /* storage blocked */ }
      if (location.hash) saved = 'cards';
      state.view = (params.get('view') || saved) === 'table' ? 'table' : 'cards';
      buildTable();
    }
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

    function buildTable() {
      const head = table.columns.map(col => col.key
        ? `<th scope="col"><button type="button" data-sort="${esc(col.key)}">${esc(col.label)}<span class="sort-mark" aria-hidden="true"></span></button></th>`
        : `<th scope="col">${esc(col.label)}</th>`).join('');
      table.el.innerHTML = `<table class="catalog-table"><thead><tr>${head}</tr></thead><tbody></tbody></table>`;
      const body = table.el.querySelector('tbody');
      cards.forEach((card, i) => {
        card.order = i;
        card.row = document.createElement('tr');
        card.row.innerHTML = table.columns.map(col => `<td class="col-${esc(col.key || 'extra')}">${col.cell(card.el)}</td>`).join('');
        card.sortValues = Object.fromEntries(table.columns.map((col, j) => [col.key,
          col.sort ? col.sort(card.el) : card.row.children[j].textContent.trim().toLowerCase()]).filter(([key]) => key));
        body.appendChild(card.row);
      });

      table.el.querySelector('thead').addEventListener('click', e => {
        const btn = e.target.closest('[data-sort]');
        if (!btn) return;
        // Ascending, then descending, then back to the page's own order.
        const key = btn.dataset.sort;
        state.sort = state.sort === key ? `-${key}` : state.sort === `-${key}` ? '' : key;
        render();
      });
      // A name opens that card in the card view.
      body.addEventListener('click', e => {
        const a = e.target.closest('[data-card]');
        if (!a) return;
        e.preventDefault();
        setView('cards');
        history.replaceState(null, '', `${location.pathname}${location.search}#${a.dataset.card}`);
        document.getElementById(a.dataset.card).scrollIntoView();
      });
      table.toggle.innerHTML = [['cards', 'Cards'], ['table', 'Table']].map(([view, label]) =>
        `<button type="button" data-view="${view}">${label}</button>`).join('');
      table.toggle.addEventListener('click', e => {
        const btn = e.target.closest('[data-view]');
        if (btn) setView(btn.dataset.view);
      });
    }

    function setView(view) {
      state.view = view;
      try { localStorage.setItem('catalog-view', view); } catch (e) { /* storage blocked */ }
      render();
    }

    function sortRows() {
      const key = state.sort.replace(/^-/, '');
      const dir = state.sort.startsWith('-') ? -1 : 1;
      const known = key in (cards[0] ? cards[0].sortValues : {});
      const sorted = [...cards].sort((a, b) => {
        if (!known) return a.order - b.order;
        const x = a.sortValues[key], y = b.sortValues[key];
        const c = typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y));
        return dir * c || a.order - b.order;
      });
      const body = table.el.querySelector('tbody');
      sorted.forEach(card => body.appendChild(card.row));
      table.el.querySelectorAll('[data-sort]').forEach(btn => {
        const on = known && btn.dataset.sort === key;
        btn.closest('th').setAttribute('aria-sort', on ? (dir > 0 ? 'ascending' : 'descending') : 'none');
        btn.querySelector('.sort-mark').textContent = on ? (dir > 0 ? ' ▲' : ' ▼') : '';
      });
    }

    function render() {
      let shown = 0;
      cards.forEach(card => {
        const show = matches(card);
        card.el.style.display = show ? '' : 'none';
        if (card.row) card.row.hidden = !show;
        if (show) shown++;
      });
      if (table) {
        grid.hidden = state.view === 'table';
        table.el.hidden = state.view !== 'table' || shown === 0;
        table.toggle.querySelectorAll('[data-view]').forEach(btn =>
          btn.setAttribute('aria-pressed', String(btn.dataset.view === state.view)));
        sortRows();
      }
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
      if (table && state.view === 'table') {
        url.set('view', 'table');
        if (state.sort) url.set('sort', state.sort);
      }
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

  return { init, esc, links, name, withRelated, RELATED };
})();
