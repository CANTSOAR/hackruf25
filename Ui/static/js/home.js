// Smooth typewriter + layered floaters + intro splash
(() => {
  // -------- Intro (once per session) --------
  const intro = document.getElementById('intro');
  const INTRO_KEY = 'scarlet_intro_seen';
  function playIntro() {
    if (!intro) return;
    if (sessionStorage.getItem(INTRO_KEY) === '1') { intro.classList.add('hidden'); return; }
    intro.classList.remove('hidden');
    setTimeout(() => { intro.classList.add('hidden'); sessionStorage.setItem(INTRO_KEY,'1'); }, 1800);
  }

  // -------- Typewriter (calm) --------
  const typeEl = document.getElementById('type');
  const text = "Welcome to ScarletAgent";
  let i = 0;
  function typeStep() {
    if (!typeEl) return;
    i = Math.min(i + 1, text.length);
    typeEl.textContent = text.slice(0, i);
    if (i < text.length) setTimeout(typeStep, 80 + Math.random()*40);
  }

  // -------- Layered floaters (cover whole screen) --------
  const wrap = document.getElementById('floaters');
  const rSrc = (document.querySelector('.hero-r')?.src) || '/static/images/rutgers_r_transparent.png'; // fallback

  const layers = [
    { every: 1300, size:[18,38], speed:[14,18], alpha:.22, z:0 }, // back
    { every:  950, size:[26,56], speed:[10,14], alpha:.28, z:1 }, // mid
    { every:  800, size:[34,72], speed:[ 8,11], alpha:.34, z:2 }  // front
  ];

  function spawn(layer){
    if(!wrap || !rSrc) return;
    const el = document.createElement('div');
    el.className = 'floater';
    el.style.backgroundImage = `url(${rSrc})`;

    // Random start anywhere from 2–98% vh, drift a bit
    const fromLeft = Math.random() > 0.5;
    const yStart = 2 + Math.random()*96;
    const yEnd   = Math.min(98, Math.max(2, yStart + (Math.random()*30 - 15)));

    const xStart = fromLeft ? '-20vw' : '120vw';
    const xEnd   = fromLeft ? '120vw' : '-20vw';

    const size = randBetween(layer.size[0], layer.size[1]);
    const dur  = randBetween(layer.speed[0], layer.speed[1]);
    const spin = (Math.random() * 120 + 80) + 'deg';

    el.style.setProperty('--xStart', xStart);
    el.style.setProperty('--xEnd',   xEnd);
    el.style.setProperty('--yStart', yStart + 'vh');
    el.style.setProperty('--yEnd',   yEnd   + 'vh');
    el.style.setProperty('--scale',  (size/72).toFixed(2));
    el.style.setProperty('--rot',    (Math.floor(Math.random()*90)-45) + 'deg');
    el.style.setProperty('--spin',   spin);
    el.style.setProperty('--alpha',  layer.alpha);
    el.style.setProperty('--dur',    dur + 's');

    el.style.width = size + 'px';
    el.style.height = size + 'px';
    el.style.zIndex = String(layer.z);

    wrap.appendChild(el);
    setTimeout(()=> el.remove(), dur*1000 + 400);
  }

  function randBetween(a,b){ return Math.round(a + Math.random()*(b-a)); }

  function startFloaters(){
    // initial sprinkle
    layers.forEach((L, idx) => { for(let k=0;k<3;k++) setTimeout(()=>spawn(L), 140*(idx+k)); });
    // steady stream
    layers.forEach(L => setInterval(()=>spawn(L), L.every));
  }

  // Kickoff
  playIntro();
  setTimeout(typeStep, 140);
  startFloaters();
})();