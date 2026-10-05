// Countries page: link the status table and the map (hover either, the other lights up).

const map = document.getElementById('map');
document.querySelectorAll('tr.row').forEach(row => {
  const iso = row.dataset.iso, link = row.querySelector('a.cname');
  const path = map?.querySelector(`a[data-iso="${iso}"] path`);
  row.addEventListener('click', e => { if (!e.target.closest('a') && link) location.href = link.href; });
  row.addEventListener('mouseenter', () => path?.classList.add('hl'));
  row.addEventListener('mouseleave', () => path?.classList.remove('hl'));
});
map?.querySelectorAll('a[data-iso]').forEach(a => {
  const row = document.querySelector(`tr.row[data-iso="${a.dataset.iso}"]`);
  a.addEventListener('mouseenter', () => row?.classList.add('hl'));
  a.addEventListener('mouseleave', () => row?.classList.remove('hl'));
});
