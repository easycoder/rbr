const toggle = document.querySelector('.menu-toggle');
const nav = document.querySelector('#main-nav');
toggle.addEventListener('click', () => {
  const isOpen = nav.classList.toggle('open');
  toggle.setAttribute('aria-expanded', String(isOpen));
  toggle.setAttribute('aria-label', isOpen ? 'Close navigation' : 'Open navigation');
});
nav.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
  nav.classList.remove('open');
  toggle.setAttribute('aria-expanded', 'false');
  toggle.setAttribute('aria-label', 'Open navigation');
}));
// The hero has three photos (index.html picks one before first paint). The div
// that names it is display:none today, so this only matters if it is ever
// shown — but a label describing a different couple would be worse than none.
const heroPhoto = document.querySelector('.hero-photo');
const heroVariant = document.documentElement.getAttribute('data-hero');
if (heroPhoto && heroVariant === 'mixed') {
  heroPhoto.setAttribute('aria-label', heroPhoto.dataset.labelMixed);
} else if (heroPhoto && heroVariant === 'alternate') {
  heroPhoto.setAttribute('aria-label', heroPhoto.dataset.labelAlternate);
}

document.querySelector('#year').textContent = new Date().getFullYear();
