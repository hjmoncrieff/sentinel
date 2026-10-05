// Country monitor: the country picker, and the timeline readout for in-depth monitors.

document.getElementById('c-pick')?.addEventListener('change', e => { location.href = e.target.value; });

const read = document.getElementById('tl-read');
if (read) {
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const show = m => {
    read.innerHTML = `<span class="d">${esc(m.dataset.date)}<br>${esc(m.dataset.kind)}</span><div><h3>${esc(m.dataset.title)}</h3><p>${esc(m.dataset.desc)}</p></div>`;
  };
  document.querySelectorAll('#tl .tl-m').forEach(m => {
    m.style.cursor = 'pointer';
    for (const type of ['mouseenter', 'click', 'focus']) m.addEventListener(type, () => show(m));
  });
}
