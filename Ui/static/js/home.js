// Intro splash + typewriter + floating Rs (uses your existing CSS classes)
(() => {
  // ---- Intro (once per session) ----
  const intro = document.getElementById('intro');
  const INTRO_KEY = 'scarlet_intro_seen';
  function playIntro() {
    if (!intro) return;
    if (sessionStorage.getItem(INTRO_KEY) === '1') {
      intro.classList.add('hidden');
      return;
    }
    intro.classList.remove('hidden');
    setTimeout(() => {
      intro.classList.add('hidden');
      sessionStorage.setItem(INTRO_KEY, '1');
    }, 1600);
  }

  // ---- Typewriter (white + red split) ----
  const L = document.getElementById('type-left');
  const R = document.getElementById('type-right');
  const leftText  = 'Welcome to';
  const rightText = ' ScarletAgent';
  let i = 0;
  function typeStep() {
    if (!L || !R) return;
    if (i <= leftText.length) {
      L.textContent = leftText.slice(0, i);
      R.textContent = '';
    } else {
      L.textContent = leftText;
      R.textContent = rightText.slice(0, i - leftText.length);
    }
    i++;
    const total = leftText.length + rightText.length;
    if (i <= total) setTimeout(typeStep, 90 + Math.random() * 35);
  }

  // ---- Floating R’s ----
  const floatersWrap = document.getElementById('floaters');
  const rSrc = document.querySelector('.hero-r')?.getAttribute('src');
  function spawnFloater() {
    if (!floatersWrap || !rSrc) return;
    const el = document.createElement('div');
    el.className = 'floater';
    el.style.backgroundImage = `url(${rSrc})`;

    const fromLeft = Math.random() > 0.5;
    const y = 10 + Math.random() * 80;          // 10–90vh
    const size = 28 + Math.random() * 48;       // 28–76px
    const dur = 9 + Math.random() * 9;          // 9–18s

    el.style.top = `${y}vh`;
    el.style.width = el.style.height = `${size}px`;
    el.style.setProperty('--xStart', fromLeft ? '-15vw' : '115vw');
    el.style.setProperty('--xEnd',   fromLeft ? '115vw'  : '-15vw');
    el.style.setProperty('--yStart', `${(Math.random() * -20).toFixed(0)}vh`);
    el.style.setProperty('--yEnd',   `${(Math.random() *  20).toFixed(0)}vh`);
    el.style.setProperty('--rot',  `${(Math.random() * 90 - 45).toFixed(0)}deg`);
    el.style.setProperty('--spin', `${(Math.random() * 90 - 45).toFixed(0)}deg`);
    el.style.setProperty('--scale', (0.65 + Math.random() * 0.7).toFixed(2));
    el.style.setProperty('--alpha', '0.85');
    el.style.setProperty('--dur',   `${dur.toFixed(1)}s`);

    floatersWrap.appendChild(el);
    setTimeout(() => el.remove(), dur * 1000 + 400);
  }

  function startFloaters() {
    for (let k = 0; k < 4; k++) setTimeout(spawnFloater, 180 * k);
    setInterval(spawnFloater, 1000);
  }

  // Start when DOM is ready
  document.addEventListener('DOMContentLoaded', () => {
    playIntro();
    setTimeout(typeStep, 120);
    startFloaters();
  });
})();