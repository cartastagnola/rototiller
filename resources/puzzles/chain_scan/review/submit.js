
// ---- submit: send the reviewed names, Claude writes them in layered_puzzles.json ----
const submitBtn = document.getElementById('submitBtn');
const subInfo = document.getElementById('subInfo');
function submission() {
  const names = [], noVerdict = [], noSuggestion = [], stalePending = [];
  for (const it of ITEMS) {
    if (!it.hash) continue;
    const s = get(it.id), sug = (s.suggestion || '').trim();
    if (s.status === 'ok') { if (stale(it.id)) stalePending.push(it); else names.push({ id: it.id, name: nameFor(it), verdict: 'ok', family: famOf(it), tags: shownTags(it) }); }
    else if (s.status === 'change') { if (sug) names.push({ id: it.id, name: sug, verdict: 'change', family: famOf(it), tags: shownTags(it) }); else noSuggestion.push(it); }
    else noVerdict.push(it);
  }
  return { names, noVerdict, noSuggestion, stalePending };
}
submitBtn.addEventListener('click', () => {
  const sub = submission();
  panel.replaceChildren(); panel.hidden = false;
  panel.append(el('p', 'ptitle', `${sub.names.length} names will be submitted.`));
  panel.append(el('p', null, 'OK rows use the name shown, Change rows use your better name. Claude checks them and writes them in layered_puzzles.json.'));
  const skipped = [[sub.noVerdict, 'without a verdict'], [sub.noSuggestion, 'marked Change without a better name'], [sub.stalePending, 'changed after OK (check them again)']]
    .filter(([l]) => l.length).map(([l, why]) => `${l.length} ${why}`);
  if (skipped.length) panel.append(el('p', 'pwarn', 'Not submitted: ' + skipped.join(', ') + '.'));
  const bar = el('div', 'pbar');
  const ok = el('button', 'pbtn primary', 'Submit'); ok.type = 'button'; ok.disabled = !sub.names.length || !store;
  const cancel = el('button', 'pbtn', 'Cancel'); cancel.type = 'button';
  ok.addEventListener('click', async () => {
    ok.disabled = true;
    const id = 's-' + Date.now();
    try {
      await store.collection('submissions').doc(id).set({ status: 'pending', createdAt: new Date().toISOString(), count: sub.names.length, separator: applied.sep, names: sub.names });
      panel.hidden = true; setStatus(`Submitted ${sub.names.length} names. Ask Claude to apply the submission.`);
    } catch (e) { ok.disabled = false; setStatus('Could not submit (' + (e && e.code || 'error') + ').', true); }
  });
  cancel.addEventListener('click', () => { panel.hidden = true; });
  if (!store) bar.append(el('span', 'pwarn', 'Not connected: open the page on claude.ai to submit.'));
  bar.append(ok, cancel); panel.append(bar); cancel.focus();
});
(async () => {
  const db = window.claude && window.claude.use ? await window.claude.use('db') : null;
  if (!db) return;
  db.collection('submissions').orderBy('createdAt', 'desc').limit(1).onSnapshot(snap => {
    const d = snap.docs[0]; if (!d) { subInfo.textContent = ''; return; }
    const b = d.data() || {}, when = (b.createdAt || '').slice(0, 16).replace('T', ' ');
    subInfo.textContent = b.status === 'applied' ? `Last submission (${when}): applied. ${b.result || ''}`
      : b.status === 'rejected' ? `Last submission (${when}): not applied. ${b.result || ''}`
      : `Last submission (${when}): ${b.count} names, waiting for Claude.`;
    subInfo.classList.toggle('warn', b.status === 'rejected');
  }, () => {});
})();
