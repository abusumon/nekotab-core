/*
 * Searchable dropdowns.
 *
 * Turns long <select> elements (15+ options) into a type-to-search box. The
 * original <select> stays in the form, visually hidden, and is what actually
 * gets submitted, so server-side form handling is unchanged.
 *
 * Opt in or out per element with data-searchable="on" / "off".
 * Selects inside Vue apps (#vueMount) are left alone.
 *
 * data-choices-src="<id>" reads options from a <script type="application/json">
 * element instead of the <select>'s own <option>s: an array of
 * [value, label, secondaryText, listFirst]. Pages with many identical
 * dropdowns (e.g. one institution dropdown per conflict row) render the
 * list once instead of once per row.
 */
(function () {
  'use strict';

  var MIN_OPTIONS = 15;
  var MAX_RENDERED = 100;
  var sources = {};
  var uid = 0;

  function normalise(s) {
    return String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/\s+/g, ' ').trim();
  }

  function itemsFromSource(id) {
    if (!sources[id]) {
      var el = document.getElementById(id);
      var raw = [];
      try { raw = el ? JSON.parse(el.textContent) : []; } catch (e) { raw = []; }
      sources[id] = raw.map(function (r) {
        // r[2] (e.g. an institution's code) is shown under the label, which
        // tells apart institutions that share a name.
        return { value: String(r[0]), label: r[1], sub: r[2] || '', search: normalise(r[1] + ' ' + (r[2] || '')), top: !!r[3] };
      });
    }
    return sources[id];
  }

  function itemsFromSelect(select) {
    var items = [];
    Array.prototype.forEach.call(select.options, function (opt) {
      if (opt.value === '') return;  // the blank choice is offered separately
      var group = opt.parentNode.tagName === 'OPTGROUP' ? opt.parentNode.label : '';
      items.push({ value: opt.value, label: opt.text, search: normalise(opt.text + ' ' + group), group: group, disabled: opt.disabled });
    });
    return items;
  }

  function blankOption(select) {
    for (var i = 0; i < select.options.length; i++) {
      if (select.options[i].value === '') return select.options[i];
    }
    return null;
  }

  function enhance(select) {
    if (select.dataset.ssReady) return;
    select.dataset.ssReady = '1';

    var srcId = select.dataset.choicesSrc;
    var listId = 'ss-list-' + (++uid);
    var wrap = document.createElement('div');
    wrap.className = 'ss';
    var input = document.createElement('input');
    input.type = 'text';
    input.className = 'ss-input form-control' + (select.classList.contains('is-invalid') ? ' is-invalid' : '');
    if (select.classList.contains('form-control-sm')) input.classList.add('form-control-sm');
    input.autocomplete = 'off';
    input.spellcheck = false;
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-expanded', 'false');
    input.setAttribute('aria-controls', listId);
    var label = select.id && document.querySelector('label[for="' + select.id + '"]');
    if (label) {
      // Point the visible label at the search box rather than the hidden select.
      input.id = select.id + '-search';
      label.setAttribute('for', input.id);
    } else if (select.getAttribute('aria-label')) {
      input.setAttribute('aria-label', select.getAttribute('aria-label'));
    }
    var list = document.createElement('ul');
    list.className = 'ss-list';
    list.id = listId;
    list.setAttribute('role', 'listbox');
    list.hidden = true;
    wrap.appendChild(input);
    wrap.appendChild(list);
    select.parentNode.insertBefore(wrap, select.nextSibling);
    select.classList.add('ss-native');
    select.tabIndex = -1;
    select.setAttribute('aria-hidden', 'true');

    var active = -1;
    var shown = [];
    var placeholder = (blankOption(select) || {}).text || '';
    input.placeholder = select.dataset.searchPlaceholder || 'Type to search…';

    function items() { return srcId ? itemsFromSource(srcId) : itemsFromSelect(select); }

    function currentLabel() {
      var opt = select.options[select.selectedIndex];
      return opt && opt.value !== '' ? opt.text : '';
    }

    function syncFromSelect() {
      input.value = currentLabel();
      input.disabled = select.disabled;
    }

    function choose(item) {
      var value = item ? item.value : '';
      if (value !== '' && !Array.prototype.some.call(select.options, function (o) { return o.value === value; })) {
        select.appendChild(new Option(item.label, value));
      }
      var changed = select.value !== value;
      select.value = value;
      input.value = item ? item.label : '';
      input.classList.remove('is-invalid');
      close();
      if (changed) {
        select.dispatchEvent(new Event('input', { bubbles: true }));
        select.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }

    function render(query) {
      var q = normalise(query);
      var words = q ? q.split(' ') : [];
      var all = items();
      var matches = words.length ? all.filter(function (it) {
        return words.every(function (w) { return it.search.indexOf(w) !== -1; });
      }) : all.slice();
      matches.sort(function (a, b) {
        if (a.top !== b.top) return a.top ? -1 : 1;
        if (!q) return 0;
        return (a.search.indexOf(q) === 0 ? 0 : 1) - (b.search.indexOf(q) === 0 ? 0 : 1);
      });

      list.innerHTML = '';
      shown = [];
      var blank = blankOption(select);
      if (blank && !q && !select.required) shown.push({ value: '', label: placeholder || '—', blank: true });
      matches.slice(0, MAX_RENDERED).forEach(function (it) { shown.push(it); });

      var lastGroup = null;
      shown.forEach(function (it, i) {
        if (it.group && it.group !== lastGroup && !q) {
          var g = document.createElement('li');
          g.className = 'ss-group';
          g.textContent = it.group;
          list.appendChild(g);
        }
        lastGroup = it.group;
        var li = document.createElement('li');
        li.className = 'ss-option' + (it.blank ? ' ss-blank' : '') + (it.disabled ? ' ss-disabled' : '');
        li.id = listId + '-' + i;
        li.setAttribute('role', 'option');
        li.textContent = it.label;
        var secondary = it.sub || (q ? it.group : '');
        if (secondary) {
          var small = document.createElement('small');
          small.textContent = secondary;
          li.appendChild(small);
        }
        if (it.value === select.value) li.setAttribute('aria-selected', 'true');
        li.addEventListener('mousedown', function (e) { e.preventDefault(); });
        li.addEventListener('click', function () { if (!it.disabled) choose(it.blank ? null : it); });
        list.appendChild(li);
      });

      if (!matches.length) {
        var none = document.createElement('li');
        none.className = 'ss-note';
        none.textContent = select.dataset.noMatches || 'No matches';
        list.appendChild(none);
      } else if (matches.length > MAX_RENDERED) {
        var more = document.createElement('li');
        more.className = 'ss-note';
        more.textContent = (matches.length - MAX_RENDERED) + ' more. Keep typing to narrow it down.';
        list.appendChild(more);
      }
      setActive(shown.length ? 0 : -1);
    }

    function setActive(i) {
      var nodes = list.querySelectorAll('.ss-option');
      Array.prototype.forEach.call(nodes, function (n) { n.classList.remove('ss-active'); });
      active = i;
      if (i >= 0 && nodes[i]) {
        nodes[i].classList.add('ss-active');
        input.setAttribute('aria-activedescendant', nodes[i].id);
        var top = nodes[i].offsetTop, bottom = top + nodes[i].offsetHeight;
        if (top < list.scrollTop) list.scrollTop = top;
        else if (bottom > list.scrollTop + list.clientHeight) list.scrollTop = bottom - list.clientHeight;
      } else {
        input.removeAttribute('aria-activedescendant');
      }
    }

    function open() {
      if (select.disabled) return;
      render('');
      list.hidden = false;
      wrap.classList.add('ss-open');
      input.setAttribute('aria-expanded', 'true');
      var sel = list.querySelector('[aria-selected="true"]');
      if (sel) setActive(Array.prototype.indexOf.call(list.querySelectorAll('.ss-option'), sel));
    }

    function close() {
      list.hidden = true;
      wrap.classList.remove('ss-open');
      input.setAttribute('aria-expanded', 'false');
      input.removeAttribute('aria-activedescendant');
    }

    input.addEventListener('focus', function () { input.select(); open(); });
    input.addEventListener('click', function () { if (list.hidden) open(); });
    input.addEventListener('input', function () {
      if (list.hidden) { list.hidden = false; wrap.classList.add('ss-open'); input.setAttribute('aria-expanded', 'true'); }
      render(input.value);
    });
    input.addEventListener('blur', function () { close(); input.value = currentLabel(); });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); if (list.hidden) open(); else setActive(Math.min(active + 1, shown.length - 1)); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(Math.max(active - 1, 0)); }
      else if (e.key === 'Enter') {
        if (!list.hidden) {
          e.preventDefault();  // pick the option instead of submitting the form
          if (active >= 0 && shown[active] && !shown[active].disabled) choose(shown[active].blank ? null : shown[active]);
        }
      }
      else if (e.key === 'Escape') { if (!list.hidden) { e.preventDefault(); close(); input.value = currentLabel(); } }
    });

    select.addEventListener('change', syncFromSelect);
    select.addEventListener('invalid', function () { input.classList.add('is-invalid'); input.focus(); });
    if (select.form) select.form.addEventListener('reset', function () { setTimeout(syncFromSelect, 0); });

    syncFromSelect();
  }

  function shouldEnhance(select) {
    if (select.multiple || select.size > 1 || select.dataset.ssReady) return false;
    if (select.dataset.searchable === 'off') return false;
    if (select.closest('#vueMount, [data-vue-root]')) return false;
    if (select.dataset.searchable === 'on' || select.dataset.choicesSrc) return true;
    return select.options.length >= MIN_OPTIONS;
  }

  function scan(root) {
    Array.prototype.forEach.call((root || document).querySelectorAll('select'), function (s) {
      if (shouldEnhance(s)) enhance(s);
    });
  }

  window.SearchableSelect = { scan: scan, enhance: enhance };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { scan(document); });
  else scan(document);
})();
