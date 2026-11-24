// Homepage background: rings of agents exchange messages, and each ring seeds the next generation.
// The system zooms outward without end, so generations keep appearing at the centre. No text.
(function () {
  const cv = document.getElementById('bgfx');
  if (!cv) return;
  const ctx = cv.getContext('2d');
  const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // low-saturation palette shared with the site
  const HUES = [[108,132,150],[79,125,113],[111,101,144],[154,74,87],[63,106,140]];
  const LINE = [159,176,191];
  const N = 7;              // agents per generation
  const K = 1.62;           // radius ratio between consecutive generations
  const PERIOD = 14;        // seconds for one generation to grow into the next
  const GENS = 7;           // rings drawn at once

  let W = 0, H = 0, dpr = 1, cx = 0, cy = 0, base = 0, running = true, t0 = performance.now();

  function rand(seed) { let s = seed * 9301 + 49297; return () => ((s = (s * 9301 + 49297) % 233280) / 233280); }

  // deterministic layout per generation index so the loop never repeats visibly
  function agents(g) {
    const r = rand(g * 17 + 3), off = r() * Math.PI * 2, out = [];
    for (let i = 0; i < N; i++) out.push({ a: off + i * 2 * Math.PI / N + (r() - 0.5) * 0.35, j: 0.85 + r() * 0.3, s: r() });
    return out;
  }
  function pairs(g) {
    const r = rand(g * 31 + 7), out = [];
    for (let i = 0; i < N; i++) { let j = Math.floor(r() * N); if (j === i) j = (j + 2) % N; out.push([i, j, r()]); }
    return out;
  }
  const cache = new Map();
  function gen(g) { if (!cache.has(g)) { cache.set(g, { ag: agents(g), pr: pairs(g), hue: HUES[((g % HUES.length) + HUES.length) % HUES.length] }); if (cache.size > 40) cache.delete(cache.keys().next().value); } return cache.get(g); }

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    const rect = cv.getBoundingClientRect();
    W = rect.width; H = rect.height;
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    cx = W * 0.5; cy = Math.min(H * 0.46, 420);
    base = Math.max(W, H) * 0.045;
  }

  function rgba(c, a) { return `rgba(${c[0]},${c[1]},${c[2]},${a})`; }
  function pos(g, i, z, time) {
    const G = gen(g), A = G.ag[i];
    const R = base * Math.pow(K, g - z) * A.j;
    const ang = A.a + time * 0.018 * (g % 2 ? 1 : -1);
    return [cx + Math.cos(ang) * R, cy + Math.sin(ang) * R * 0.78];
  }
  // fade in near the centre, fade out toward the edge of the canvas
  function ringAlpha(g, z) {
    const u = g - z;                       // position in ring units
    const fin = Math.min(1, Math.max(0, (u + 0.6) / 1.6));
    const fout = Math.min(1, Math.max(0, (GENS - 1.2 - u) / 2.2));
    return fin * fout;
  }

  function draw(now) {
    const time = (now - t0) / 1000;
    const z = time / PERIOD;               // continuous generation index at the centre
    const g0 = Math.floor(z) - 1;
    ctx.clearRect(0, 0, W, H);

    // faint core
    const core = ctx.createRadialGradient(cx, cy, 0, cx, cy, base * 3.2);
    core.addColorStop(0, 'rgba(108,132,150,0.10)'); core.addColorStop(1, 'rgba(108,132,150,0)');
    ctx.fillStyle = core; ctx.beginPath(); ctx.arc(cx, cy, base * 3.2, 0, Math.PI * 2); ctx.fill();

    for (let g = g0; g < g0 + GENS; g++) {
      const a = ringAlpha(g, z); if (a <= 0.01) continue;
      const G = gen(g), Gn = gen(g + 1), an = ringAlpha(g + 1, z);

      // lineage: each agent seeds two agents of the next generation
      if (an > 0.01) for (let i = 0; i < N; i++) for (const d of [0, 3]) {
        const j = (i + d) % N, p = pos(g, i, z, time), q = pos(g + 1, j, z, time);
        const mx = (p[0] + q[0]) / 2 + (cy - (p[1] + q[1]) / 2) * 0.12, my = (p[1] + q[1]) / 2 + ((p[0] + q[0]) / 2 - cx) * 0.12;
        ctx.strokeStyle = rgba(LINE, 0.24 * Math.min(a, an)); ctx.lineWidth = 0.9;
        ctx.beginPath(); ctx.moveTo(p[0], p[1]); ctx.quadraticCurveTo(mx, my, q[0], q[1]); ctx.stroke();
        // a slow pulse travels outward along the lineage: the next generation learns from this one
        const s = ((time / 9) + G.ag[i].s + d * 0.37) % 1, e = s * s * (3 - 2 * s);
        const bx = (1 - e) * (1 - e) * p[0] + 2 * (1 - e) * e * mx + e * e * q[0], by = (1 - e) * (1 - e) * p[1] + 2 * (1 - e) * e * my + e * e * q[1];
        ctx.fillStyle = rgba(G.hue, 0.5 * Math.min(a, an) * Math.sin(Math.PI * s)); ctx.beginPath(); ctx.arc(bx, by, 2.2, 0, Math.PI * 2); ctx.fill();
      }

      // interaction inside the generation: curved links and messages passed between agents
      for (const [i, j, ph] of G.pr) {
        const p = pos(g, i, z, time), q = pos(g, j, z, time);
        const mx = (p[0] + q[0]) / 2 + (cx - (p[0] + q[0]) / 2) * 0.35, my = (p[1] + q[1]) / 2 + (cy - (p[1] + q[1]) / 2) * 0.35;
        ctx.strokeStyle = rgba(G.hue, 0.2 * a); ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(p[0], p[1]); ctx.quadraticCurveTo(mx, my, q[0], q[1]); ctx.stroke();
        for (let k = 0; k < 3; k++) {
          const s = ((time / 5.5) + ph + k * 0.06) % 1, e = s;
          const bx = (1 - e) * (1 - e) * p[0] + 2 * (1 - e) * e * mx + e * e * q[0], by = (1 - e) * (1 - e) * p[1] + 2 * (1 - e) * e * my + e * e * q[1];
          ctx.fillStyle = rgba(G.hue, (0.6 - k * 0.17) * a * Math.sin(Math.PI * s)); ctx.beginPath(); ctx.arc(bx, by, 2.6 - k * 0.6, 0, Math.PI * 2); ctx.fill();
        }
      }

      // agents: soft discs with a slow breathing halo
      const scale = Math.pow(K, (g - z) * 0.45);
      for (let i = 0; i < N; i++) {
        const p = pos(g, i, z, time), r = Math.max(2.2, Math.min(9, 3.4 * scale));
        const br = 0.5 + 0.5 * Math.sin(time * 0.6 + G.ag[i].s * 6.28);
        const halo = ctx.createRadialGradient(p[0], p[1], 0, p[0], p[1], r * 4);
        halo.addColorStop(0, rgba(G.hue, 0.28 * a * (0.6 + 0.4 * br))); halo.addColorStop(1, rgba(G.hue, 0));
        ctx.fillStyle = halo; ctx.beginPath(); ctx.arc(p[0], p[1], r * 4, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = rgba([255, 255, 255], 0.85 * a); ctx.beginPath(); ctx.arc(p[0], p[1], r, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = rgba(G.hue, 0.55 * a); ctx.lineWidth = 1.1; ctx.stroke();
      }
    }
  }

  function loop(now) { if (running) { draw(now); requestAnimationFrame(loop); } }
  resize();
  window.addEventListener('resize', resize);
  if (reduce) { draw(t0 + 6000); return; }
  document.addEventListener('visibilitychange', () => { const was = running; running = !document.hidden; if (running && !was) requestAnimationFrame(loop); });
  if ('IntersectionObserver' in window) new IntersectionObserver(es => { const was = running; running = es[0].isIntersecting && !document.hidden; if (running && !was) requestAnimationFrame(loop); }).observe(cv);
  requestAnimationFrame(loop);
})();
