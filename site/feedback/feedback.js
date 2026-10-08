// site/feedback/feedback.js: visitor notes on a plannit site (spec: the project's FEEDBACK-SPEC.md).
// publish.sh adds it to every page: <script src="/feedback/feedback.js" data-api="/feedback/api.php" defer>.
//  - every figure with an <img data-base> (the presentation gallery and plan) gets a 💬 button with a count;
//    the note records the file shown at that moment, so palette, day/night and furnished/empty are in its name.
//  - while a figure's panel is open, a tap on the image drops a pin there (fractions of width and height).
//  - one general box at the foot of the page.
// Notes are private: the page only ever learns the counts.
(function () {
  const me = document.currentScript;
  const API = (me && me.dataset.api) || '/feedback/api.php';
  const T = {
    btn:     { el: 'Σχόλιο', en: 'Note' },
    title:   { el: 'Σχόλιο για αυτή την εικόνα', en: 'A note on this image' },
    gtitle:  { el: 'Σχόλια, προτάσεις, διορθώσεις', en: 'Comments, suggestions, corrections' },
    gintro:  { el: 'Για τη σελίδα ή τον σχεδιασμό γενικά. Για μια συγκεκριμένη εικόνα, πατήστε το 💬 κάτω από αυτήν.',
               en: 'About the page or the design in general. For one image, use the 💬 under it.' },
    text:    { el: 'Τι προσέξατε;', en: 'What did you notice?' },
    name:    { el: 'Όνομα (προαιρετικό)', en: 'Name (optional)' },
    pin:     { el: 'Προαιρετικά: πατήστε πάνω στην εικόνα για να δείξετε το σημείο.', en: 'Optional: tap the image to point at the spot.' },
    pinned:  { el: 'Το σημείο σημειώθηκε· πατήστε ξανά για να το μετακινήσετε.', en: 'Spot marked; tap again to move it.' },
    send:    { el: 'Αποστολή', en: 'Send' },
    cancel:  { el: 'Άκυρο', en: 'Cancel' },
    sending: { el: 'Αποστολή…', en: 'Sending…' },
    thanks:  { el: 'Ελήφθη, ευχαριστούμε.', en: 'Received, thank you.' },
    fail:    { el: 'Δεν στάλθηκε: ', en: 'Not sent: ' },
    count:   { el: n => n === 1 ? '1 σχόλιο' : n + ' σχόλια', en: n => n === 1 ? '1 note' : n + ' notes' },
  };
  const lang = () => (document.documentElement.lang || 'en').toLowerCase().startsWith('el') ? 'el' : 'en';
  const tr = (k, ...a) => { const v = T[k][lang()]; return typeof v === 'function' ? v(...a) : v; };
  const relabel = root => root.querySelectorAll('[data-fb]').forEach(e => {
    const k = e.dataset.fb, at = e.dataset.fbAttr;
    if (at) e.setAttribute(at, tr(k)); else e.textContent = tr(k);
  });
  const h = (tag, cls, attrs) => { const e = document.createElement(tag); if (cls) e.className = cls; Object.assign(e, attrs || {}); return e; };
  const lbl = (tag, cls, key) => { const e = h(tag, cls); e.dataset.fb = key; return e; };

  let counts = {};
  const shown = img => decodeURIComponent(img.src.split('?')[0].split('/').pop());

  // ---------------------------------------------------------------- the note form (shared by both kinds)
  function form(ctx) {
    const f = h('form', 'fb-form'); f.noValidate = true;
    const ta = h('textarea', 'fb-text', { rows: 3, maxLength: 2000, required: true });
    ta.dataset.fb = 'text'; ta.dataset.fbAttr = 'placeholder';
    const nm = h('input', 'fb-name', { type: 'text', maxLength: 80, autocomplete: 'name' });
    nm.dataset.fb = 'name'; nm.dataset.fbAttr = 'placeholder';
    try { nm.value = localStorage.getItem('fb-name') || ''; } catch (e) {}
    const hp = h('input', 'fb-hp', { type: 'text', name: 'website', tabIndex: -1, autocomplete: 'off' });
    hp.setAttribute('aria-hidden', 'true');
    const row = h('div', 'fb-row');
    const send = lbl('button', 'fb-send', 'send'); send.type = 'submit';
    const status = h('span', 'fb-status'); status.setAttribute('role', 'status');
    row.append(send);
    if (ctx.cancel) { const c = lbl('button', 'fb-cancel', 'cancel'); c.type = 'button'; c.onclick = ctx.cancel; row.append(c); }
    row.append(status);
    f.append(ta, nm, hp, row);
    f.onsubmit = async ev => {
      ev.preventDefault();
      if (!ta.value.trim()) { ta.focus(); return; }
      const note = Object.assign({ text: ta.value, name: nm.value, website: hp.value, page: location.pathname, lang: lang() }, ctx.target());
      try { localStorage.setItem('fb-name', nm.value); } catch (e) {}
      send.disabled = true; status.textContent = tr('sending');
      try {
        const r = await fetch(API, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(note) });
        const j = await r.json().catch(() => ({}));
        if (!r.ok || !j.ok) throw new Error(j.error || r.status);
        ta.value = ''; status.textContent = tr('thanks');
        const k = note.image || '_general'; counts[k] = (counts[k] || 0) + 1; paint();
        ctx.done && setTimeout(ctx.done, 1600);
      } catch (e) { status.textContent = tr('fail') + e.message; }
      send.disabled = false;
    };
    return f;
  }

  // ---------------------------------------------------------------- per image
  const figs = [];
  function addFigure(fig) {
    const img = fig.querySelector('img[data-base]'); if (!img) return;
    const host = img.parentElement; host.classList.add('fb-host');
    const btn = h('button', 'fb-btn', { type: 'button' }); btn.setAttribute('aria-expanded', 'false');
    const n = h('span', 'fb-n');
    btn.append('💬 ', n);
    const panel = h('div', 'fb-panel'); panel.hidden = true;
    const hint = lbl('p', 'fb-hint', 'pin');
    let pin = null, dot = null;
    const close = () => { panel.hidden = true; btn.setAttribute('aria-expanded', 'false'); fig.classList.remove('fb-pinning');
                          pin = null; dot && dot.remove(); dot = null; hint.dataset.fb = 'pin'; relabel(panel); };
    panel.append(lbl('h4', 'fb-title', 'title'), hint,
                 form({ target: () => ({ image: shown(img), view: img.dataset.base, pin }), cancel: close, done: close }));
    btn.onclick = () => {
      if (!panel.hidden) return close();
      panel.hidden = false; btn.setAttribute('aria-expanded', 'true'); fig.classList.add('fb-pinning');
      relabel(panel); panel.querySelector('textarea').focus({ preventScroll: true });
    };
    // in pin mode a tap on the image marks the spot instead of opening the lightbox
    host.addEventListener('click', ev => {
      if (panel.hidden) return;
      ev.preventDefault(); ev.stopImmediatePropagation();
      const r = img.getBoundingClientRect();
      pin = [+((ev.clientX - r.left) / r.width).toFixed(4), +((ev.clientY - r.top) / r.height).toFixed(4)];
      if (pin[0] < 0 || pin[0] > 1 || pin[1] < 0 || pin[1] > 1) { pin = null; return; }
      if (!dot) { dot = h('span', 'fb-pin', { textContent: '1' }); host.append(dot); }
      dot.style.left = (img.offsetLeft + pin[0] * img.offsetWidth) + 'px';
      dot.style.top = (img.offsetTop + pin[1] * img.offsetHeight) + 'px';
      hint.dataset.fb = 'pinned'; relabel(panel);
    }, true);
    const controls = fig.querySelector('.controls');
    (controls || fig).append(btn);
    (controls ? controls.after.bind(controls) : fig.append.bind(fig))(panel);
    new MutationObserver(paint).observe(img, { attributes: true, attributeFilter: ['src'] });
    figs.push({ img, btn, n });
  }

  // ---------------------------------------------------------------- the general box
  function addGeneral() {
    const s = h('section', 'fb-general');
    s.append(lbl('h3', 'fb-title', 'gtitle'), lbl('p', 'fb-hint', 'gintro'), form({ target: () => ({ image: '', view: '' }) }));
    const foot = document.querySelector('.wrap > footer, body > footer, footer');
    if (foot) foot.before(s); else (document.querySelector('main') || document.body).append(s);
    return s;
  }

  function paint() {
    for (const f of figs) {
      const c = counts[shown(f.img)] || 0;
      f.n.textContent = c ? c : '';
      f.btn.title = c ? tr('count', c) : tr('btn');
      f.btn.setAttribute('aria-label', tr('btn') + (c ? ' (' + tr('count', c) + ')' : ''));
    }
  }

  function init() {
    document.querySelectorAll('figure').forEach(addFigure);
    addGeneral();
    relabel(document);
    // the page's own language toggle rewrites <html lang>; follow it
    new MutationObserver(() => { relabel(document); paint(); }).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
    paint();
    fetch(API + '?counts', { cache: 'no-store' }).then(r => r.json()).then(j => { counts = j || {}; paint(); }).catch(() => {});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
