(() => {
  const scene = document.querySelector('[data-landing-welcome-scene]');
  const el = document.querySelector('[data-landing-welcome]');
  const canvas = document.querySelector('[data-landing-welcome-fireworks]');
  if (!scene || !el) return;

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const colors = ['#ff6b6b', '#ffd93d', '#6bcb77', '#4d96ff', '#ff85c0', '#ffe8a8', '#a855f7', '#22d3ee'];
  let particles = [];
  let raf = 0;
  let running = false;

  const removeScene = () => {
    running = false;
    if (raf) cancelAnimationFrame(raf);
    scene.remove();
  };

  const burst = (x, y, power = 1) => {
    const count = Math.floor(36 + power * 24);
    for (let i = 0; i < count; i += 1) {
      const angle = (Math.PI * 2 * i) / count + (Math.random() - 0.5) * 0.35;
      const speed = (2.2 + Math.random() * 3.6) * power;
      particles.push({
        x,
        y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        life: 1,
        decay: 0.01 + Math.random() * 0.012,
        color: colors[Math.floor(Math.random() * colors.length)],
        size: 1.5 + Math.random() * 2.5,
      });
    }
  };

  const resizeCanvas = () => {
    if (!canvas) return;
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(window.innerWidth * ratio);
    canvas.height = Math.floor(window.innerHeight * ratio);
    canvas.style.width = `${window.innerWidth}px`;
    canvas.style.height = `${window.innerHeight}px`;
    const ctx = canvas.getContext('2d');
    if (ctx) ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  };

  const draw = () => {
    if (!canvas || !running) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
    particles = particles.filter((p) => p.life > 0);
    for (const p of particles) {
      p.x += p.vx;
      p.y += p.vy;
      p.vy += 0.055;
      p.vx *= 0.985;
      p.life -= p.decay;
      ctx.globalAlpha = Math.max(p.life, 0);
      ctx.fillStyle = p.color;
      ctx.shadowColor = p.color;
      ctx.shadowBlur = 8;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size * p.life, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
    ctx.shadowBlur = 0;
    if (particles.length > 0 || running) raf = requestAnimationFrame(draw);
  };

  const startFireworks = () => {
    if (!canvas || reduced) return;
    resizeCanvas();
    running = true;
    const rect = el.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height * 0.35;
    burst(cx, cy, 1.15);
    window.setTimeout(() => burst(cx - 95, cy + 28, 0.95), 320);
    window.setTimeout(() => burst(cx + 105, cy + 18, 1), 680);
    window.setTimeout(() => burst(window.innerWidth * 0.28, cy + 50, 0.75), 1050);
    window.setTimeout(() => burst(window.innerWidth * 0.72, cy + 42, 0.8), 1380);
    draw();
    window.addEventListener('resize', resizeCanvas, {passive: true});
    scene.addEventListener('transitionend', () => {
      window.removeEventListener('resize', resizeCanvas);
    }, {once: true});
  };

  const show = () => {
    scene.classList.add('is-visible');
    el.classList.add('is-visible');
    if (!reduced) window.setTimeout(startFireworks, 180);
  };

  const hide = () => {
    scene.classList.add('is-leaving');
    el.classList.add('is-leaving');
    running = false;
    scene.addEventListener('transitionend', removeScene, {once: true});
    window.setTimeout(removeScene, 700);
  };

  if (reduced) {
    show();
    window.setTimeout(hide, 3600);
    return;
  }

  requestAnimationFrame(show);
  window.setTimeout(hide, 4800);
})();