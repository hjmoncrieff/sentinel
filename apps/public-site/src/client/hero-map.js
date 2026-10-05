// Front-page map: the SVG is drawn at build time. This adds the country card (hover,
// focus, click to pin), layer switching, subregion zoom and the two-way strip highlight.

const svg = document.getElementById('hero-map');
if (svg) {
  const data = JSON.parse(document.getElementById('hm-data').textContent);
  const zooms = JSON.parse(svg.dataset.zooms);
  const stage = svg.parentNode;
  const card = document.getElementById('hm-card');
  let pinned = null;

  const show = (iso, x, y, pin) => {
    card.innerHTML = data.cards[iso]; card.hidden = false; card.classList.toggle('pinned', !!pin);
    card.querySelector('.hm-x').hidden = !pin; card.querySelector('.hm-hint').hidden = !!pin;
    const sw = stage.clientWidth, sh = stage.clientHeight;
    card.style.left = Math.min(Math.max(8, x + 14), sw - card.offsetWidth - 8) + 'px';
    card.style.top = Math.min(Math.max(8, y - 20), Math.max(8, sh - card.offsetHeight - 8)) + 'px';
  };
  const hide = () => { if (!pinned) card.hidden = true; };
  const highlight = (iso, on) => {
    svg.querySelectorAll(`[data-iso="${iso}"]`).forEach(n => n.classList.toggle('hm-hl', on));
    document.querySelectorAll(`.ov-strip li[data-iso="${iso}"]`).forEach(li => li.classList.toggle('hl', on));
  };
  const at = ev => { const r = stage.getBoundingClientRect(); return [ev.clientX - r.left, ev.clientY - r.top]; };
  const centerOf = node => { const b = node.getBoundingClientRect(), r = stage.getBoundingClientRect(); return [b.left + b.width / 2 - r.left, b.top + b.height / 2 - r.top]; };

  svg.querySelectorAll('.hm-c').forEach(node => {
    const iso = node.dataset.iso;
    node.style.cursor = 'pointer';
    node.addEventListener('mouseenter', e => { highlight(iso, true); if (!pinned) show(iso, ...at(e), false); });
    node.addEventListener('mousemove', e => { if (!pinned) show(iso, ...at(e), false); });
    node.addEventListener('mouseleave', () => { highlight(iso, false); hide(); });
    node.addEventListener('focus', () => { highlight(iso, true); if (!pinned) show(iso, ...centerOf(node), false); });
    node.addEventListener('blur', () => { highlight(iso, false); hide(); });
    node.addEventListener('click', e => { e.stopPropagation(); pinned = iso; show(iso, ...at(e), true); });
    node.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pinned = iso; show(iso, ...centerOf(node), true); } });
  });
  const unpin = () => { pinned = null; card.hidden = true; };
  card.addEventListener('click', e => { if (e.target.closest('.hm-x')) unpin(); e.stopPropagation(); });
  stage.addEventListener('click', unpin);
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && pinned) unpin(); });

  document.querySelector('.hm-layers').addEventListener('click', e => {
    const b = e.target.closest('[data-layer]'); if (!b) return;
    document.querySelectorAll('.hm-layers button').forEach(x => x.setAttribute('aria-checked', x === b));
    svg.querySelectorAll('.hm-c').forEach(n => n.setAttribute('fill', n.dataset[b.dataset.layer]));
    document.getElementById('hm-legend').innerHTML = data.legends[b.dataset.layer] + data.marks;
  });

  // Zoom by easing the viewBox between prepared boxes; page scroll is left alone.
  let frame = 0;
  const zoomTo = key => {
    document.querySelectorAll('.hm-zooms button').forEach(b => b.setAttribute('aria-pressed', b.dataset.zoom === key));
    const from = svg.getAttribute('viewBox').split(' ').map(Number), to = zooms[key];
    cancelAnimationFrame(frame);
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) { svg.setAttribute('viewBox', to.join(' ')); return; }
    const t0 = performance.now(), dur = 550;
    const step = now => {
      const p = Math.min(1, (now - t0) / dur), k = p < .5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2;
      svg.setAttribute('viewBox', from.map((v, i) => (v + (to[i] - v) * k).toFixed(1)).join(' '));
      if (p < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
  };
  document.querySelector('.hm-zooms').addEventListener('click', e => { const b = e.target.closest('[data-zoom]'); if (b) { unpin(); zoomTo(b.dataset.zoom); } });

  document.querySelectorAll('.ov-strip li').forEach(li => {
    li.addEventListener('mouseenter', () => highlight(li.dataset.iso, true));
    li.addEventListener('mouseleave', () => highlight(li.dataset.iso, false));
  });
}
