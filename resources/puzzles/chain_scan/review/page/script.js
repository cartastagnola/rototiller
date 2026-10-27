const ITEMS = JSON.parse(document.getElementById('data').textContent);
const byId = new Map(ITEMS.map(it => [it.id, it]));
const RULE_ITEMS = ITEMS.filter(it => it.rule);
const state = new Map();          // id -> {status, suggestion, note, savedName}
const rows = new Map();           // id -> row parts
let filter = 'all', query = '', current = null, store = null, view = 'names';
// the rule decisions the names are built from: a tag changed in the "Project tags" tab renames
// every name that uses it right away
const SEP_RULE = ITEMS.find(it => it.rule && it.rule.kind === 'sep');
const SEP_DEFAULT = SEP_RULE ? SEP_RULE.rule.proposed : ': ';
const NO_DECISIONS = { tags: {}, suffix: null, wording: {}, sep: SEP_DEFAULT };
let applied = NO_DECISIONS;
// tab of a row: the families, the project tags, or the name format (separator)
const viewOf = it => !it.rule ? 'names' : it.rule.kind === 'tag' ? 'tags' : it.rule.kind === 'families' ? 'families' : it.rule.kind === 'ptags' ? 'ptags' : 'format';
// tabs that are settings: no verdicts, no filters
const SETTING_VIEWS = ['format', 'families', 'ptags'];
// ':' -> ': ', '-' -> ' - ' (spaces around, except after a colon)
function normSep(v) { const t = (v || '').trim(); return !t ? SEP_DEFAULT : t === ':' ? ': ' : ` ${t} `; }
// two names that differ only by the separator are the same name (an OK stays valid)
const sepless = n => (n || '').replace(/^([A-Z][A-Z0-9_]*)\s*[^A-Za-z0-9_\s]+\s*/, '$1|');
function refreshDecisions() { const d = decisionsNow(); if (same(d, applied)) return false; applied = d; return true; }

const LOCAL_KEY = 'puzzle-names-review';
function loadLocal() { try { return JSON.parse(localStorage.getItem(LOCAL_KEY) || '{}'); } catch { return {}; } }
function saveLocal() { try { localStorage.setItem(LOCAL_KEY, JSON.stringify(Object.fromEntries(state))); } catch {} }

const get = id => state.get(id) || { status: '', suggestion: '', note: '', savedName: '', tag: '' };
// tag of a family row: its own, or the one it was moved to with the Move button
const tagOf = it => get(it.id).tag || it.tagBase;
// family of a family row (coin family in puzzle_types.json): the one chosen on the row, else its default
const famOf = it => get(it.id).family || it.family;
// puzzle tags of a row: the family first (chosen on the row), then the others; a row keeps its
// default ones (layered_puzzles.json, else from the layers) until they are changed on the row
const ptagsOf = it => get(it.id).ptags || it.ptags || [];
const shownTags = it => [famOf(it), ...ptagsOf(it).filter(t => t !== famOf(it))];
const PT_RULE = ITEMS.find(it => it.rule && it.rule.kind === 'ptags');
let addedPtags = [];   // puzzle tags created in the Puzzle tags tab (meta/ptags in the store)
try { addedPtags = JSON.parse(localStorage.getItem('layered-names-review-ptags') || '[]'); } catch {}
function allPuzzleTags() {
  const base = PT_RULE ? [...PT_RULE.rule.saved, ...PT_RULE.rule.layers] : [];
  const used = ITEMS.filter(it => it.hash).flatMap(ptagsOf);
  return [...new Set([...base, ...addedPtags, ...used])].sort((a, b) => a.localeCompare(b));
}
const FAM_RULE = ITEMS.find(it => it.rule && it.rule.kind === 'families');
const BASE_FAMILIES = FAM_RULE ? FAM_RULE.rule.families : [];
let addedFamilies = [];   // families added in the Families tab (meta/families in the store)
try { addedFamilies = JSON.parse(localStorage.getItem('layered-names-review-families') || '[]'); } catch {}
function allFamilies() {
  const used = ITEMS.filter(it => it.hash).flatMap(it => [it.family, famOf(it)]);
  return [...new Set([...BASE_FAMILIES, ...addedFamilies, ...used])].sort();
}
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };

// ---- names from rules ----
function decisionsNow() {
  const d = { tags: {}, suffix: null, wording: {}, sep: SEP_DEFAULT };
  for (const it of RULE_ITEMS) {
    const s = get(it.id), sug = (s.suggestion || '').trim();
    if (it.rule.kind === 'tag' && sug && sug !== it.rule.tag) d.tags[it.rule.tag] = sug;
    if (it.rule.kind === 'suffix' && sug && sug !== it.rule.term) d.suffix = sug;
    if (it.rule.kind === 'wording' && s.status === 'change') d.wording[it.id] = sug;
    if (it.rule.kind === 'sep' && sug) d.sep = normSep(sug);
  }
  return d;
}
const savedName = it => it.saved && it.saved.names.length === 1 && it.saved.keys === it.saved.total ? it.saved.names[0] : null;
// the name shown and approved with OK is always the proposal; the name already in
// layered_puzzles.json is shown below it (Change pre-fills it, to keep it)
function nameFor(it, dec = applied) { return proposalFor(it, dec); }
const tagChanged = it => !!(it.hash && applied.tags[tagOf(it)]);
const untagged = it => nameFor(it, { ...applied, tags: {} });
const renamedByTag = it => tagChanged(it) && untagged(it) !== nameFor(it);
const FAMILY_ITEMS = ITEMS.filter(it => it.hash);
const TAGS = ITEMS.filter(it => it.rule && it.rule.kind === 'tag').map(it => it.rule.tag);
const tagUsers = tag => FAMILY_ITEMS.filter(it => tagOf(it) === tag);   // the names that start with the tag
function proposalFor(it, dec = applied) {
  if (it.rule && it.rule.kind === 'sep') return `PROJECT_TAG${dec.sep}what it does`;
  if (!it.hash) return it.proposed;
  const base = tagOf(it), tag = dec.tags[base] || base;
  const suffix = dec.suffix ? it.tagSuffix.replace('_RUE', dec.suffix) : it.tagSuffix;
  let desc = it.desc;
  // moved to another tag: the new tag is not repeated at the start, the old one goes at the end
  // (CAT_V2 - CIRCUIT treasury -> CIRCUIT - treasury (CAT_V2))
  if (base !== it.tagBase) {
    if (desc.toUpperCase().startsWith(base + ' ')) desc = desc.slice(base.length + 1);
    desc += ` (${dec.tags[it.tagBase] || it.tagBase})`;
  }
  for (const [rid, sug] of Object.entries(dec.wording)) {
    const r = byId.get(rid).rule;
    const hit = (r.alts && r.alts[it.id] != null) || (r.targets && r.targets.includes(it.id));
    if (!hit) continue;
    if (sug && r.term && desc.includes(r.term)) desc = desc.replace(r.term, sug);
    else if (r.alts && r.alts[it.id] != null) desc = r.alts[it.id];
    else if (r.altTerm) desc = desc.replace(r.term, r.altTerm);
  }
  return `${tag}${suffix}${dec.sep}${desc}`;
}
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const stale = id => { const s = get(id); return s.status === 'ok' && !!s.savedName && sepless(s.savedName) !== sepless(nameFor(byId.get(id))); };

// ---- build the list once ----
const list = document.getElementById('list');
const groups = new Map();
for (const it of ITEMS) { if (!groups.has(it.group)) groups.set(it.group, []); groups.get(it.group).push(it); }
const groupEls = new Map();
let sepInput = null, sepSection = null, sepExample = null;
let famSection = null, famBody = null;
let ptSection = null, ptBody = null;
for (const [name, items] of groups) {
  if (items[0].rule && items[0].rule.kind === 'sep') { buildSeparatorSetting(items[0]); continue; }
  if (items[0].rule && items[0].rule.kind === 'families') { buildFamiliesSetting(); continue; }
  if (items[0].rule && items[0].rule.kind === 'ptags') { buildPtagsSetting(); continue; }
  const sec = el('section', 'group'); sec.dataset.group = name;
  const head = el('div', 'ghead');
  const h2 = el('h2', null, name); head.append(h2);
  const cnt = el('span', 'gcount'); head.append(cnt);
  const isRules = items.some(it => it.rule);
  const all = el('button', 'gall', 'Mark the rest OK'); all.type = 'button';
  all.title = 'Mark every row of this group without a verdict as OK';
  all.addEventListener('click', () => groupEls.get(name).items.forEach(it => { if (!get(it.id).status) setField(it.id, { status: 'ok' }); }));
  head.append(all); sec.append(head);
  if (isRules) sec.append(el('p', 'ghint', 'Write a better project tag: every name that uses it changes right away, marked "project tag changed" in the Names tab.'));
  for (const it of items) sec.append(buildRow(it));
  list.append(sec); groupEls.set(name, { sec, cnt, h2, items, tag: isRules ? null : name });
}
const emptyEl = el('p', 'empty', 'Nothing matches this filter.'); emptyEl.hidden = true; list.append(emptyEl);
// put each family row in the group of its tag (after a Move, or when the saved verdicts load)
function placeRows() {
  for (const g of groupEls.values()) {
    if (!g.tag) continue;
    const members = FAMILY_ITEMS.filter(it => tagOf(it) === g.tag).sort((a, b) => b.seen - a.seen);
    if (same(members.map(it => it.id), g.items.map(it => it.id))) continue;
    g.items = members;
    for (const it of members) g.sec.append(rows.get(it.id).r);
  }
}

// Name format tab: a setting, not a row to review. The separator is saved like a verdict
// (the suggestion of the separator item), so it is kept and submitted with the names
function buildSeparatorSetting(it) {
  sepSection = el('section', 'group setting'); sepSection.hidden = true;
  const head = el('div', 'ghead'); head.append(el('h2', null, 'Name format')); sepSection.append(head);
  const lab = el('label', 'setfield', 'Separator between the project tag and what the puzzle does');
  sepInput = el('input'); sepInput.id = 'sep-input'; sepInput.placeholder = SEP_DEFAULT.trim(); sepInput.autocomplete = 'off';
  lab.append(sepInput); sepSection.append(lab);
  sepExample = el('p', 'setex'); sepSection.append(sepExample);
  let timer = null;
  sepInput.addEventListener('input', () => {
    state.set(it.id, { ...get(it.id), suggestion: sepInput.value });
    refreshDecisions(); repaintAll();
    clearTimeout(timer); timer = setTimeout(() => write(it.id), 700);
  });
  list.append(sepSection);
}
function paintSeparator() {
  if (!sepInput) return;
  if (document.activeElement !== sepInput) sepInput.value = (get(SEP_RULE.id).suggestion || '').trim() || SEP_DEFAULT.trim();
  const ex = ITEMS.find(i => i.hash);
  sepExample.textContent = 'Example: ' + (ex ? nameFor(ex) : `PROJECT_TAG${applied.sep}what it does`);
  sepSection.hidden = view !== 'format';
}
// Families tab: the families in puzzle_types.json, the ones added here, and how many names use each
const famKey = v => v.toUpperCase().replace(/[^A-Z0-9]+/g, '_').replace(/^_+|_+$/g, '');
function buildFamiliesSetting() {
  famSection = el('section', 'group setting'); famSection.hidden = true;
  const head = el('div', 'ghead'); head.append(el('h2', null, 'Families')); famSection.append(head);
  famSection.append(el('p', 'ghint', 'The family is the coin type (CAT, SINGLETON, STD…), not the project: the project is the project tag at the start of the name. Choose it on each row in the Names tab; add a new coin type here.'));
  const t = el('table', 'famtable'), thead = el('tr');
  for (const h of ['family', 'names', 'from', '']) thead.append(el('th', null, h));
  famBody = el('tbody'); t.append(el('thead'), famBody); t.firstChild.append(thead); famSection.append(t);
  const add = el('div', 'famadd'), inp = el('input'), b = el('button', 'pbtn primary', 'Add family');
  inp.placeholder = 'NEW_FAMILY'; inp.setAttribute('aria-label', 'New family'); b.type = 'button';
  const doAdd = () => {
    const f = famKey(inp.value); if (!f) return;
    if (!allFamilies().includes(f)) { addedFamilies = [...addedFamilies, f]; saveFamilies(); }
    inp.value = ''; repaintAll(); setStatus(`Family ${f} added: choose it on a row in the Names tab.`);
  };
  b.addEventListener('click', doAdd);
  inp.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); doAdd(); } });
  add.append(inp, b); famSection.append(add);
  list.append(famSection);
}
function paintFamilies() {
  if (!famSection) return;
  famSection.hidden = view !== 'families';
  if (famSection.hidden) return;
  const fams = FAMILY_ITEMS.map(famOf);
  famBody.replaceChildren(...allFamilies().map(f => {
    const tr = el('tr'), n = fams.filter(x => x === f).length;
    tr.append(el('td', null, f), el('td', 'n', String(n)),
      el('td', null, BASE_FAMILIES.includes(f) ? 'puzzle_types.json' : addedFamilies.includes(f) ? 'added here' : 'chosen on a row'));
    const td = el('td');
    if (addedFamilies.includes(f) && !n) {
      const rm = el('button', 'pbtn', 'Remove'); rm.type = 'button';
      rm.addEventListener('click', () => { addedFamilies = addedFamilies.filter(x => x !== f); saveFamilies(); repaintAll(); });
      td.append(rm);
    }
    tr.append(td); return tr;
  }));
}
// Puzzle tags tab: every puzzle tag, how many rows have it, and a field to create one
function buildPtagsSetting() {
  ptSection = el('section', 'group setting'); ptSection.hidden = true;
  const head = el('div', 'ghead'); head.append(el('h2', null, 'Puzzle tags')); ptSection.append(head);
  ptSection.append(el('p', 'ghint', 'Puzzle tags are written in the tags list of layered_puzzles.json, after the family. A row starts with the ones already saved, else one per known layer. Add or remove them on each row in the Names tab; create a new one here. Families are puzzle tags too: a row can also get another family as a puzzle tag.'));
  const t = el('table', 'famtable'), thead = el('tr');
  for (const h of ['puzzle tag', 'rows', 'from', '']) thead.append(el('th', null, h));
  ptBody = el('tbody'); t.append(el('thead'), ptBody); t.firstChild.append(thead); ptSection.append(t);
  const add = el('div', 'famadd'), inp = el('input'), b = el('button', 'pbtn primary', 'Create puzzle tag');
  inp.placeholder = 'new_puzzle_tag'; inp.setAttribute('aria-label', 'New puzzle tag'); b.type = 'button';
  const doAdd = () => {
    const v = inp.value.trim().replace(/\s+/g, '_'); if (!v) return;
    if (!allPuzzleTags().includes(v)) { addedPtags = [...addedPtags, v]; savePtags(); }
    inp.value = ''; repaintAll(); setStatus(`Puzzle tag ${v} created: add it on a row in the Names tab.`);
  };
  b.addEventListener('click', doAdd);
  inp.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); doAdd(); } });
  add.append(inp, b); ptSection.append(add);
  list.append(ptSection);
}
function paintPtags() {
  if (!ptSection) return;
  ptSection.hidden = view !== 'ptags';
  if (ptSection.hidden) return;
  const rowsTags = FAMILY_ITEMS.map(ptagsOf);
  ptBody.replaceChildren(...allPuzzleTags().map(tg => {
    const tr = el('tr'), n = rowsTags.filter(x => x.includes(tg)).length;
    tr.append(el('td', null, tg), el('td', 'n', String(n)),
      el('td', null, PT_RULE.rule.saved.includes(tg) ? 'layered_puzzles.json' : PT_RULE.rule.layers.includes(tg) ? 'a layer' : addedPtags.includes(tg) ? 'created here' : 'added on a row'));
    const td = el('td');
    if (addedPtags.includes(tg) && !n) {
      const rm = el('button', 'pbtn', 'Remove'); rm.type = 'button';
      rm.addEventListener('click', () => { addedPtags = addedPtags.filter(x => x !== tg); savePtags(); repaintAll(); });
      td.append(rm);
    }
    tr.append(td); return tr;
  }));
}
function savePtags() {
  try { localStorage.setItem('layered-names-review-ptags', JSON.stringify(addedPtags)); } catch {}
  if (store) store.collection('meta').doc('ptags').set({ list: addedPtags, updatedAt: new Date().toISOString() })
    .catch(e => setStatus('Could not save the puzzle tags (' + (e && e.code || 'error') + ').', true));
}
// a row's puzzle tags after adding or removing one; the default list again is saved as no change
function setPtags(it, tags) {
  const def = it.ptags || [];
  setField(it.id, { ptags: same(tags, def) ? null : tags });
}
function saveFamilies() {
  try { localStorage.setItem('layered-names-review-families', JSON.stringify(addedFamilies)); } catch {}
  if (store) store.collection('meta').doc('families').set({ list: addedFamilies, updatedAt: new Date().toISOString() })
    .catch(e => setStatus('Could not save the families (' + (e && e.code || 'error') + ').', true));
}
function buildRow(it) {
  const r = el('div', 'row'); r.tabIndex = 0; r.dataset.id = it.id;
  r.append(el('span', 'stripe'));
  const main = el('div', 'main');
  const prop = el('div', 'prop');
  const pfx = el('span', 'pfx'), txt = document.createTextNode('');
  prop.append(pfx, txt);
  if (it.unsure) prop.append(el('span', 'tag unsure', 'guessed'));
  const staleTag = el('span', 'tag stale', 'changed after OK'); staleTag.hidden = true; prop.append(staleTag);
  const retagTag = el('span', 'tag retag', 'project tag changed'); retagTag.hidden = true; prop.append(retagTag);
  const movedTag = el('span', 'tag moved'); movedTag.hidden = true; prop.append(movedTag);
  const sugTag = el('span', 'tag sugg'); sugTag.hidden = true; prop.append(sugTag);
  const noteTag = el('span', 'tag noted', 'note'); noteTag.hidden = true; prop.append(noteTag);
  main.append(prop);
  if (it.saved) {
    const sv = el('div', 'prop savedname', it.saved.names.join('; '));
    sv.title = 'Name in layered_puzzles.json' + (it.saved.types && it.saved.types.length ? ', type ' + it.saved.types.join(', ') : '');
    sv.append(el('span', 'tag saved', it.saved.keys < it.saved.total ? `already named (${it.saved.keys} of ${it.saved.total} kinds)` : 'already named'));
    main.append(sv);
  }
  const meta = el('div', 'meta');
  meta.textContent = it.current + (it.file ? '  ·  ' + it.file : '') + (it.hash ? '  ·  ' : '');
  if (it.hash) meta.append(el('span', 'h', it.hash.slice(0, 10) + '…'));
  main.append(meta);
  let famSel = null, famLine = null;
  if (it.hash) {
    famLine = el('label', 'famline', 'family (coin type)');
    famSel = el('select'); famSel.addEventListener('change', () => setField(it.id, { family: famSel.value === it.family ? '' : famSel.value }));
    famLine.append(famSel); main.append(famLine);
  }
  let ptLine = null, ptChips = null, ptAdd = null;
  if (it.hash) {
    ptLine = el('div', 'ptline'); ptLine.append(el('span', 'ptlabel', 'puzzle tags'));
    ptChips = el('span', 'ptchips'); ptLine.append(ptChips);
    ptAdd = el('select', 'ptadd'); ptAdd.setAttribute('aria-label', 'Add a puzzle tag');
    ptAdd.addEventListener('change', () => { const v = ptAdd.value; if (v) setPtags(it, [...ptagsOf(it), v]); });
    ptLine.append(ptAdd); main.append(ptLine);
  }
  const retagLine = el('div', 'meta retag'); retagLine.hidden = true; main.append(retagLine);
  const was = el('div', 'meta was'); was.hidden = true; main.append(was);
  r.append(main);
  const acts = el('div', 'acts');
  const bOk = el('button', 'b-ok', 'OK'), bCh = el('button', 'b-ch', 'Change'), bNote = el('button', 'b-note', 'Note');
  [bOk, bCh, bNote].forEach(b => { b.type = 'button'; b.setAttribute('aria-pressed', 'false'); });
  bOk.addEventListener('click', () => { if (stale(it.id)) setField(it.id, { status: 'ok' }); else toggleStatus(it.id, 'ok'); });
  bCh.addEventListener('click', () => { toggleStatus(it.id, 'change'); if (get(it.id).status === 'change') { prefill(it.id); openEditor(it.id, 'sugg'); } });
  bNote.addEventListener('click', () => openEditor(it.id, 'note', true));
  acts.append(bOk, bCh, bNote);
  // Move: put the row under another project tag (e.g. a CAT_V2 row of CIRCUIT under CIRCUIT)
  let move = null;
  if (it.hash) {
    const bMove = el('button', 'b-move', 'Move'); bMove.type = 'button'; bMove.title = 'Move to another project tag (m)';
    move = el('select', 'moveto'); move.hidden = true; move.setAttribute('aria-label', 'Move to project tag');
    bMove.addEventListener('click', () => openMove(it.id));
    move.addEventListener('change', () => { const t = move.value; move.hidden = true; setField(it.id, { tag: t === it.tagBase ? '' : t }); rows.get(it.id).r.focus(); });
    move.addEventListener('keydown', e => { if (e.key === 'Escape') { e.preventDefault(); move.hidden = true; r.focus(); } });
    move.addEventListener('blur', () => { move.hidden = true; });
    acts.append(bMove, move);
  }
  r.append(acts);
  const ed = el('div', 'editor'); ed.hidden = true;
  const l1 = el('label', null, !it.rule || it.rule.kind === 'wording' ? 'Better name' : it.rule.kind === 'sep' ? 'Better separator' : 'Better project tag');
  const sug = el('input'); sug.id = 'sug-' + it.id; l1.append(sug);
  const l2 = el('label', null, 'Note'); const note = el('textarea'); note.id = 'note-' + it.id; note.rows = 1; note.placeholder = 'Why, or what to check'; l2.append(note);
  ed.append(l1, l2); r.append(ed);
  sug.addEventListener('input', () => queueText(it.id, 'suggestion', sug.value));
  note.addEventListener('input', () => queueText(it.id, 'note', note.value));
  [sug, note].forEach(f => f.addEventListener('keydown', e => { if (e.key === 'Escape') { e.preventDefault(); flushText(it.id); r.focus(); } }));
  r.addEventListener('focus', () => setCurrent(it.id));
  rows.set(it.id, { r, pfx, txt, was, famSel, famLine, famOpts: '', ptLine, ptChips, ptAdd, ptKey: '', retagTag, retagLine, movedTag, move, bOk, bCh, bNote, ed, sug, note, sugTag, noteTag, staleTag, it });
  return r;
}

// ---- state changes ----
function toggleStatus(id, status) { setField(id, { status: get(id).status === status ? '' : status }); }
function setField(id, patch) {
  const next = { ...get(id), ...patch }; state.set(id, next);
  refreshDecisions();
  // a Move changes the name: an OK given before stays on the old name ("changed after OK")
  if (!('tag' in patch) || 'status' in patch) next.savedName = nameFor(byId.get(id));
  if ('tag' in patch) repaintAll(); else repaintFor(id);
  write(id);
}
const textTimers = new Map();
function queueText(id, field, value) {
  const s = { ...get(id), [field]: value };
  if (field === 'suggestion' && value.trim() && !s.status) s.status = 'change';
  state.set(id, s); repaintFor(id, true);
  clearTimeout(textTimers.get(id)); textTimers.set(id, setTimeout(() => { textTimers.delete(id); write(id); }, 700));
}
function flushText(id) { if (textTimers.has(id)) { clearTimeout(textTimers.get(id)); textTimers.delete(id); write(id); } }
function prefill(id) {
  const it = byId.get(id), x = rows.get(id);
  if (savedName(it) && !(get(id).suggestion || '').trim()) { x.sug.value = savedName(it); queueText(id, 'suggestion', x.sug.value); }
}
function openMove(id) {
  const x = rows.get(id), it = byId.get(id); if (!x.move) return;
  x.move.replaceChildren(...TAGS.map(t => { const o = el('option', null, (applied.tags[t] || t) + (t === it.tagBase ? '  (its own project tag)' : '')); o.value = t; return o; }));
  x.move.value = tagOf(it); x.move.hidden = false; x.move.focus();
}
function openEditor(id, which, toggle) {
  const x = rows.get(id);
  if (toggle && !x.ed.hidden && document.activeElement !== x.sug && document.activeElement !== x.note) { x.ed.hidden = true; paintRow(id); return; }
  x.ed.hidden = false; x.bNote.setAttribute('aria-pressed', 'true');
  (which === 'note' ? x.note : x.sug).focus();
}

// one write at a time per document; the latest state wins
const inflight = new Map(), dirty = new Set();
async function write(id) {
  saveLocal();
  if (!store) return;
  if (inflight.has(id)) { dirty.add(id); return; }
  const it = byId.get(id); const s = get(id);
  const body = { status: s.status || '', suggestion: s.suggestion || '', note: s.note || '', tag: s.tag || '', family: s.family || '', ptags: s.ptags || null,
                 current: it.current, proposed: s.savedName || nameFor(it), group: it.group, updatedAt: new Date().toISOString() };
  const p = store.collection('reviews').doc(id).set(body).then(() => setStatus('Saved. Claude can read your verdicts.'))
    .catch(e => setStatus(e && e.code === 'invalid_argument' ? 'You can view this page but not save verdicts.' : 'Could not save (' + (e && e.code || 'error') + '). Your last change is kept in this browser.', true))
    .finally(() => { inflight.delete(id); if (dirty.delete(id)) write(id); });
  inflight.set(id, p);
}

// panel for the submit dialog
const panel = document.getElementById('applyPanel');

// ---- painting ----
// a tag row changes names in the other tab: repaint all of them
function repaintFor(id, typing) {
  if (byId.get(id).rule) { refreshDecisions(); for (const k of rows.keys()) paintRow(k, k === id && typing); paintSummary(); }
  else { paintRow(id, typing); paintSummary(); }
}
function paintRow(id, typing) {
  const x = rows.get(id); const s = get(id); const it = x.it;
  const name = nameFor(it);
  const i = it.hash || viewOf(it) === 'format' ? name.indexOf(applied.sep) : -1;
  const cut = i > 0 ? i + applied.sep.length : 0;
  x.pfx.textContent = name.slice(0, cut); x.txt.textContent = name.slice(cut);
  const prop = proposalFor(it);
  const before = it.hash ? untagged(it) : '';
  const retagged = renamedByTag(it);
  x.retagTag.hidden = !retagged; x.retagLine.hidden = !retagged;
  if (retagged) x.retagLine.textContent = `was: ${before}  (project tag ${tagOf(it)} → ${applied.tags[tagOf(it)]})`;
  const moved = it.hash && tagOf(it) !== it.tagBase;
  x.movedTag.hidden = !moved; if (moved) x.movedTag.textContent = 'moved from ' + (applied.tags[it.tagBase] || it.tagBase);
  if (it.rule && it.rule.kind === 'tag') {
    const users = tagUsers(it.rule.tag), to = applied.tags[it.rule.tag];
    x.was.hidden = false;
    x.was.textContent = to ? `${it.rule.tag} → ${to}: renames ${users.filter(renamedByTag).length} of the ${users.length} names that use it` : `used by ${users.length} names`;
  } else { const first = proposalFor(it, { ...NO_DECISIONS, sep: applied.sep }); x.was.hidden = name === first; if (!x.was.hidden) x.was.textContent = 'first proposal: ' + it.proposed; }
  x.r.classList.toggle('st-ok', s.status === 'ok'); x.r.classList.toggle('st-change', s.status === 'change');
  const isStale = stale(id); x.staleTag.hidden = !isStale; x.r.classList.toggle('st-stale', isStale);
  x.bOk.setAttribute('aria-pressed', String(s.status === 'ok' && !isStale)); x.bCh.setAttribute('aria-pressed', String(s.status === 'change'));
  const hasSug = !!(s.suggestion || '').trim(), hasNote = !!(s.note || '').trim();
  x.sugTag.hidden = !hasSug; if (hasSug) x.sugTag.textContent = '→ ' + s.suggestion.trim();
  x.noteTag.hidden = !hasNote || !x.ed.hidden;
  x.bNote.setAttribute('aria-pressed', String(!x.ed.hidden || hasNote));
  x.sug.placeholder = it.rule && it.rule.kind === 'tag' ? it.rule.tag : it.rule && it.rule.kind === 'suffix' ? it.rule.term
    : it.rule && it.rule.kind === 'sep' ? it.rule.proposed.trim() : name;
  if (!typing) {
    if (document.activeElement !== x.sug) x.sug.value = s.suggestion || '';
    if (document.activeElement !== x.note) x.note.value = s.note || '';
  }
  if ((hasSug || hasNote) && x.ed.hidden && s.status === 'change') x.ed.hidden = false;
  if (x.famSel) {
    const fams = allFamilies(), key = fams.join('|');
    if (x.famOpts !== key) { x.famSel.replaceChildren(...fams.map(f => { const o = el('option', null, f + (f === it.family ? '  (default)' : '')); o.value = f; return o; })); x.famOpts = key; }
    x.famSel.value = famOf(it); x.famLine.classList.toggle('changed', famOf(it) !== it.family);
  }
  if (x.ptLine) {
    const tags = shownTags(it), key = tags.join('|') + '#' + allPuzzleTags().join('|') + '#' + allFamilies().join('|');
    if (x.ptKey !== key) {
      x.ptKey = key;
      x.ptChips.replaceChildren(...tags.map((tg, i) => {
        const c = el('span', i ? 'ptag' : 'ptag fam', tg);
        if (!i) { c.title = 'The family is always the first puzzle tag: change it with the family list'; return c; }
        const rm = el('button', 'ptrm', '×'); rm.type = 'button'; rm.title = 'Remove ' + tg; rm.setAttribute('aria-label', 'Remove puzzle tag ' + tg);
        rm.addEventListener('click', () => setPtags(it, ptagsOf(it).filter(t => t !== tg)));
        c.append(rm); return c;
      }));
      const free = [...allPuzzleTags(), ...allFamilies()].filter((t, i, a) => a.indexOf(t) === i && !tags.includes(t));
      const first = el('option', null, '+ puzzle tag'); first.value = '';
      x.ptAdd.replaceChildren(first, ...free.map(t => { const o = el('option', null, t); o.value = t; return o; }));
    }
    x.ptAdd.value = '';
    x.ptLine.classList.toggle('changed', !!get(it.id).ptags);
  }
  x.r.hidden = !matches(it, s, name, isStale);
}
function matches(it, s, name, isStale) {
  if (viewOf(it) !== view) return false;
  if (ptFilter && it.hash && !shownTags(it).includes(ptFilter)) return false;
  if (filter === 'tagchg' && !(renamedByTag(it) || (it.rule && applied.tags[it.rule.tag]))) return false;
  if (filter === 'todo' && s.status) return false;
  if (filter === 'ok' && s.status !== 'ok') return false;
  if (filter === 'change' && s.status !== 'change') return false;
  if (filter === 'stale' && !isStale) return false;
  if (filter === 'notes' && !((s.note || '').trim() || (s.suggestion || '').trim())) return false;
  if (filter === 'unsure' && !it.unsure) return false;
  if (filter === 'saved' && !it.saved) return false;
  if (query) {
    const hay = (name + ' ' + it.proposed + ' ' + it.current + ' ' + it.file + ' ' + (it.saved ? it.saved.names.join(' ') : '') + ' ' + (s.suggestion || '') + ' ' + (s.note || '') + ' ' + (it.hash ? shownTags(it).join(' ') : '')).toLowerCase();
    if (!query.split(/\s+/).every(w => hay.includes(w))) return false;
  }
  return true;
}
function paintSummary() {
  let ok = 0, ch = 0, st = 0;
  const inView = ITEMS.filter(it => viewOf(it) === view);
  for (const it of inView) { const s = get(it.id).status; if (s === 'ok') ok++; else if (s === 'change') ch++; if (stale(it.id)) st++; }
  const n = inView.length;
  for (const [tid, v] of [['tnames', 'names'], ['ttags', 'tags']]) {
    const its = ITEMS.filter(it => viewOf(it) === v);
    document.getElementById(tid).textContent = `${its.filter(it => get(it.id).status).length}/${its.length}`;
  }
  document.getElementById('scheme').textContent = `<PROJECT_TAG>${applied.sep}<what it does>  ·  one row per family of puzzles seen on chain`;
  document.getElementById('pcount').textContent = `${ok + ch} of ${n} reviewed`;
  document.getElementById('pok').textContent = `${ok} OK`;
  document.getElementById('pch').textContent = `${ch} to change`;
  const pst = document.getElementById('pst'); pst.hidden = !st; pst.textContent = `${st} changed after OK`;
  document.getElementById('mok').style.width = (ok / n * 100) + '%';
  document.getElementById('mch').style.width = (ch / n * 100) + '%';
  let shown = 0;
  for (const g of groupEls.values()) {
    let done = 0, vis = 0;
    for (const it of g.items) { if (get(it.id).status) done++; if (!rows.get(it.id).r.hidden) vis++; }
    g.cnt.textContent = `${done}/${g.items.length} reviewed`;
    if (g.tag) g.h2.textContent = applied.tags[g.tag] || g.tag;
    g.sec.hidden = vis === 0; shown += vis;
  }
  emptyEl.hidden = shown > 0 || SETTING_VIEWS.includes(view);
}
function repaintAll() { placeRows(); paintPtFilter(); for (const id of rows.keys()) paintRow(id); paintSummary(); paintSeparator(); paintFamilies(); paintPtags(); }
// filter by puzzle tag (families included)
let ptFilter = '', ptFilterKey = '';
const ptFilterSel = document.getElementById('ptFilter');
ptFilterSel.addEventListener('change', () => { ptFilter = ptFilterSel.value; repaintAll(); });
function paintPtFilter() {
  const tags = [...new Set([...allFamilies(), ...allPuzzleTags()])], key = tags.join('|');
  if (key !== ptFilterKey) {
    ptFilterKey = key;
    const any = el('option', null, 'puzzle tag: any'); any.value = '';
    ptFilterSel.replaceChildren(any, ...tags.map(t => { const o = el('option', null, t); o.value = t; return o; }));
    if (ptFilter && !tags.includes(ptFilter)) ptFilter = '';
  }
  ptFilterSel.value = ptFilter;
}
function setStatus(text, warn) { const s = document.getElementById('status'); s.textContent = text; s.classList.toggle('warn', !!warn); }

// ---- filters, search, keyboard ----
document.querySelectorAll('.chip[data-f]').forEach(c => c.addEventListener('click', () => {
  filter = c.dataset.f; document.querySelectorAll('.chip[data-f]').forEach(x => x.setAttribute('aria-pressed', String(x === c))); repaintAll();
}));
// order of the project tags: most used (the order of the names) or by name. The rows are
// sorted when the order is chosen or the tab opens, not while a tag is typed
let tagOrder = 'use';
try { if (localStorage.getItem(LOCAL_KEY + '-tag-order') === 'name') tagOrder = 'name'; } catch {}
const tagSort = document.getElementById('tagSort');
// Project tags tab: the tag rows; Names tab: the groups (one per tag)
function sortTags() {
  const g = groupEls.get('Project tags');
  if (g) {
    const shown = it => applied.tags[it.rule.tag] || it.rule.tag;
    const sorted = tagOrder === 'name' ? [...g.items].sort((a, b) => shown(a).localeCompare(shown(b))) : g.items;
    for (const it of sorted) g.sec.append(rows.get(it.id).r);
  }
  const fams = [...groupEls.values()].filter(x => x.tag);
  const shownTag = x => applied.tags[x.tag] || x.tag;
  if (tagOrder === 'name') fams.sort((a, b) => shownTag(a).localeCompare(shownTag(b)));
  for (const x of fams) list.insertBefore(x.sec, emptyEl);
  tagSort.querySelectorAll('.chip').forEach(x => x.setAttribute('aria-pressed', String(x.dataset.s === tagOrder)));
}
tagSort.querySelectorAll('.chip').forEach(c => c.addEventListener('click', () => {
  tagOrder = c.dataset.s; try { localStorage.setItem(LOCAL_KEY + '-tag-order', tagOrder); } catch {}
  sortTags();
}));
document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => {
  view = t.dataset.v; document.querySelectorAll('.tab').forEach(x => x.setAttribute('aria-selected', String(x === t)));
  sortTags();
  for (const sel of ['.progress', '.controls', '.keys']) document.querySelector(sel).hidden = SETTING_VIEWS.includes(view);
  current = null; repaintAll(); window.scrollTo(0, 0);
}));
document.getElementById('q').addEventListener('input', e => { query = e.target.value.trim().toLowerCase(); repaintAll(); });

function setCurrent(id) {
  if (current && rows.has(current)) rows.get(current).r.classList.remove('cur');
  current = id; rows.get(id).r.classList.add('cur');
}
function visibleIds() { return [...list.querySelectorAll('.row')].filter(r => !r.hidden).map(r => r.dataset.id); }
function move(d) {
  const ids = visibleIds(); if (!ids.length) return;
  let i = ids.indexOf(current); i = i < 0 ? 0 : Math.min(ids.length - 1, Math.max(0, i + d));
  const r = rows.get(ids[i]).r; r.focus({ preventScroll: true }); r.scrollIntoView({ block: 'nearest' });
  const bar = document.querySelector('header.bar').getBoundingClientRect().bottom;
  if (r.getBoundingClientRect().top < bar) window.scrollBy(0, r.getBoundingClientRect().top - bar - 8);
}
document.addEventListener('keydown', e => {
  const t = e.target;
  if (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || e.metaKey || e.ctrlKey || e.altKey) return;
  const k = e.key;
  if (k === 'j' || k === 'ArrowDown') { e.preventDefault(); move(1); return; }
  if (k === 'k' || k === 'ArrowUp') { e.preventDefault(); move(-1); return; }
  if (!current) return;
  if (k === 'o') { e.preventDefault(); const was = get(current).status === 'ok' && !stale(current); if (was) toggleStatus(current, 'ok'); else { setField(current, { status: 'ok' }); move(1); } }
  else if (k === 'c' || k === 'x') { e.preventDefault(); if (get(current).status !== 'change') setField(current, { status: 'change' }); prefill(current); openEditor(current, 'sugg'); }
  else if (k === 'n') { e.preventDefault(); openEditor(current, 'note'); }
  else if (k === 'm') { e.preventDefault(); openMove(current); }
  else if (k === 'u') { e.preventDefault(); setField(current, { status: '' }); }
});

// ---- start: local copy first, then the shared store ----
for (const [id, s] of Object.entries(loadLocal())) if (byId.has(id)) state.set(id, s);
refreshDecisions();
sortTags();
repaintAll();

(async () => {
  const db = window.claude && window.claude.use ? await window.claude.use('db') : null;
  if (!db) { setStatus('Not connected: verdicts are kept in this browser only, Claude cannot read them. Open the page on claude.ai while signed in.', true); return; }
  store = db;
  db.collection('meta').doc('ptags').onSnapshot(d => {
    if (!d.exists) { if (addedPtags.length) savePtags(); return; }
    addedPtags = (d.data() || {}).list || [];
    try { localStorage.setItem('layered-names-review-ptags', JSON.stringify(addedPtags)); } catch {}
    repaintAll();
  }, () => {});
  db.collection('meta').doc('families').onSnapshot(d => {
    if (!d.exists) { if (addedFamilies.length) saveFamilies(); return; }
    addedFamilies = (d.data() || {}).list || [];
    try { localStorage.setItem('layered-names-review-families', JSON.stringify(addedFamilies)); } catch {}
    repaintAll();
  }, () => {});
  let first = true;
  db.collection('reviews').onSnapshot(snap => {
    for (const d of snap.docs) {
      if (!byId.has(d.id)) continue;
      if (inflight.has(d.id) || textTimers.has(d.id)) continue;   // keep what is being typed or saved here
      const b = d.data() || {};
      state.set(d.id, { status: b.status || '', suggestion: b.suggestion || '', note: b.note || '', savedName: b.proposed || '', tag: b.tag || '', family: b.family || '', ptags: Array.isArray(b.ptags) ? b.ptags : null });
    }
    if (first) {
      first = false;
      // push verdicts made here before the store answered
      const remote = new Set(snap.docs.map(d => d.id));
      for (const [id, s] of Object.entries(loadLocal())) if (byId.has(id) && !remote.has(id) && (s.status || s.note || s.suggestion || s.tag || s.family || s.ptags)) { state.set(id, s); write(id); }
      setStatus(snap.size ? `Loaded ${snap.size} saved verdicts. Changes save as you go.` : 'Changes save as you go. Claude reads them from here.');
    }
    refreshDecisions(); repaintAll(); saveLocal();
  }, e => setStatus('Lost the connection to the review store (' + e.code + '). Reload the page.', true));
})();
