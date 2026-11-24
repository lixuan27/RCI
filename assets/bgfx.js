// Page background: rings of agents exchange messages, and each ring seeds the next generation.
// The system zooms outward without end, so generations keep appearing at the centre. No text.
// The canvas is fixed behind the page. Scrolling thins the network out (dense at the top, sparse
// further down), widens its spacing and lets its centre drift; a quiet band keeps the text column clear.
// Options on the canvas element:
//   data-strength     overall opacity multiplier (default 1)
//   data-quiet        opacity removed behind the text column, 0..1 (default 0.8)
//   data-quiet-after  scroll offset in px before the quiet band starts (default 0)
//   data-col          width of the text column in px (default 760)
(function () {
  const cv = document.getElementById('bgfx');
  if (!cv) return;
  const ctx = cv.getContext('2d');
  const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const opt = k => cv.dataset[k];
  const STRENGTH = parseFloat(opt('strength') || '1');
  const QUIET = parseFloat(opt('quiet') || '0.8');
  const QUIET_AFTER = parseFloat(opt('quietAfter') || '0');
  const COL = parseFloat(opt('col') || '760');

  // low-saturation palette shared with the site
  const HUES = [[108,132,150],[79,125,113],[111,101,144],[154,74,87],[63,106,140]];
  const LINE = [159,176,191];
  const N = 7;              // agents per generation
  const K = 1.62;           // radius ratio between consecutive generations
  const PERIOD = 14;        // seconds for one generation to grow into the next
  const GENS = 7;           // rings drawn at once

  let W = 0, H = 0, dpr = 1, cx = 0, cy = 0, base0 = 0, base = 0, running = true, t0 = performance.now();
  let prog = 0, progT = 0, quietAmt = 0;   // smoothed scroll state

  function rand(seed) { let s = seed * 9301 + 49297; return () => ((s = (s * 9301 + 49297) % 233280) / 233280); }

  // deterministic layout per generation index so the loop never repeats visibly
  function agents(g) {
    const r = rand(g * 17 + 3), off = r() * Math.PI * 2, out = [];
    for (let i = 0; i < N; i++) out.push({ a: off + i * 2 * Math.PI / N + (r() - 0.5) * 0.35, j: 0.85 + r() * 0.3, s: r() });
    // order in which agents fade out as the network thins
    const order = out.map((x, i) => [x.s, i]).sort((p, q) => p[0] - q[0]).map(x => x[1]);
    order.forEach((i, rank) => { out[i].rank = rank; });
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
    W = window.innerWidth; H = window.innerHeight;
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    base0 = Math.max(W, H) * 0.045;
  }
  function readScroll() {
    const h = document.documentElement, max = Math.max(1, h.scrollHeight - window.innerHeight);
    progT = Math.min(1, Math.max(0, window.scrollY / max));
    return window.scrollY;
  }

  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  function rgba(c, a) { return `rgba(${c[0]},${c[1]},${c[2]},${a})`; }
  function pos(g, i, z, time) {
    const G = gen(g), A = G.ag[i];
    const R = base * Math.pow(K, g - z) * A.j;
    const ang = A.a + time * 0.018 * (g % 2 ? 1 : -1);
    return [cx + Math.cos(ang) * R, cy + Math.sin(ang) * R * 0.78];
  }
  // fade in near the centre, fade out toward the edge of the screen
  function ringAlpha(g, z) {
    const u = g - z;
    const fin = clamp((u + 0.6) / 1.6, 0, 1);
    const fout = clamp((GENS - 1.2 - u) / 2.2, 0, 1);
    return fin * fout;
  }

  function draw(now) {
    const time = (now - t0) / 1000;
    const sy = readScroll();
    prog += (progT - prog) * 0.05;
    const qT = QUIET * clamp((sy - QUIET_AFTER) / 320 + (QUIET_AFTER === 0 ? 1 : 0), 0, 1);
    quietAmt += (qT - quietAmt) * 0.06;

    // scroll moves the network from dense to sparse and lets its centre drift sideways
    const dens = 1 - 0.78 * prog;
    base = base0 * (1 + 0.75 * prog);
    cx = W * (0.5 + 0.2 * Math.sin(prog * Math.PI));
    cy = H * (0.44 + 0.08 * prog);
    const vis = STRENGTH * (0.5 + 0.5 * dens);
    const keep = rank => clamp(dens * N - rank + 0.5, 0, 1);

    const z = time / PERIOD;
    const g0 = Math.floor(z) - 1;
    ctx.globalCompositeOperation = 'source-over';
    ctx.clearRect(0, 0, W, H);

    const core = ctx.createRadialGradient(cx, cy, 0, cx, cy, base * 3.2);
    core.addColorStop(0, `rgba(108,132,150,${0.10 * vis})`); core.addColorStop(1, 'rgba(108,132,150,0)');
    ctx.fillStyle = core; ctx.beginPath(); ctx.arc(cx, cy, base * 3.2, 0, Math.PI * 2); ctx.fill();

    for (let g = g0; g < g0 + GENS; g++) {
      const a = ringAlpha(g, z) * vis; if (a <= 0.01) continue;
      const G = gen(g), Gn = gen(g + 1), an = ringAlpha(g + 1, z) * vis;

      // lineage: each agent seeds two agents of the next generation
      if (an > 0.01) for (let i = 0; i < N; i++) for (const d of [0, 3]) {
        const j = (i + d) % N, w = keep(G.ag[i].rank) * keep(Gn.ag[j].rank); if (w <= 0.01) continue;
        const p = pos(g, i, z, time), q = pos(g + 1, j, z, time);
        const mx = (p[0] + q[0]) / 2 + (cy - (p[1] + q[1]) / 2) * 0.12, my = (p[1] + q[1]) / 2 + ((p[0] + q[0]) / 2 - cx) * 0.12;
        const aa = Math.min(a, an) * w;
        ctx.strokeStyle = rgba(LINE, 0.24 * aa); ctx.lineWidth = 0.9;
        ctx.beginPath(); ctx.moveTo(p[0], p[1]); ctx.quadraticCurveTo(mx, my, q[0], q[1]); ctx.stroke();
        const s = ((time / 9) + G.ag[i].s + d * 0.37) % 1, e = s * s * (3 - 2 * s);
        const bx = (1 - e) * (1 - e) * p[0] + 2 * (1 - e) * e * mx + e * e * q[0], by = (1 - e) * (1 - e) * p[1] + 2 * (1 - e) * e * my + e * e * q[1];
        ctx.fillStyle = rgba(G.hue, 0.5 * aa * Math.sin(Math.PI * s)); ctx.beginPath(); ctx.arc(bx, by, 2.2, 0, Math.PI * 2); ctx.fill();
      }

      // interaction inside the generation: curved links and messages passed between agents
      const pk = Math.max(1, Math.round(1 + 2 * dens));
      for (const [i, j, ph] of G.pr) {
        const w = keep(G.ag[i].rank) * keep(G.ag[j].rank); if (w <= 0.01) continue;
        const p = pos(g, i, z, time), q = pos(g, j, z, time);
        const mx = (p[0] + q[0]) / 2 + (cx - (p[0] + q[0]) / 2) * 0.35, my = (p[1] + q[1]) / 2 + (cy - (p[1] + q[1]) / 2) * 0.35;
        ctx.strokeStyle = rgba(G.hue, 0.2 * a * w); ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(p[0], p[1]); ctx.quadraticCurveTo(mx, my, q[0], q[1]); ctx.stroke();
        for (let k = 0; k < pk; k++) {
          const s = ((time / 5.5) + ph + k * 0.06) % 1, e = s;
          const bx = (1 - e) * (1 - e) * p[0] + 2 * (1 - e) * e * mx + e * e * q[0], by = (1 - e) * (1 - e) * p[1] + 2 * (1 - e) * e * my + e * e * q[1];
          ctx.fillStyle = rgba(G.hue, (0.6 - k * 0.17) * a * w * Math.sin(Math.PI * s)); ctx.beginPath(); ctx.arc(bx, by, 2.6 - k * 0.6, 0, Math.PI * 2); ctx.fill();
        }
      }

      // agents: soft discs with a slow breathing halo
      const scale = Math.pow(K, (g - z) * 0.45);
      for (let i = 0; i < N; i++) {
        const w = keep(G.ag[i].rank); if (w <= 0.01) continue;
        const p = pos(g, i, z, time), r = Math.max(2.2, Math.min(9, 3.4 * scale));
        const br = 0.5 + 0.5 * Math.sin(time * 0.6 + G.ag[i].s * 6.28);
        const halo = ctx.createRadialGradient(p[0], p[1], 0, p[0], p[1], r * 4);
        halo.addColorStop(0, rgba(G.hue, 0.28 * a * w * (0.6 + 0.4 * br))); halo.addColorStop(1, rgba(G.hue, 0));
        ctx.fillStyle = halo; ctx.beginPath(); ctx.arc(p[0], p[1], r * 4, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = rgba([255, 255, 255], 0.85 * a * w); ctx.beginPath(); ctx.arc(p[0], p[1], r, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = rgba(G.hue, 0.55 * a * w); ctx.lineWidth = 1.1; ctx.stroke();
      }
    }

    // quiet band behind the text column
    if (quietAmt > 0.01) {
      const mid = W / 2, half = Math.min(COL, W) / 2, soft = 90;
      const gr = ctx.createLinearGradient(mid - half - soft, 0, mid + half + soft, 0);
      const span = 2 * (half + soft), e1 = soft / span, e2 = (soft + 60) / span;
      gr.addColorStop(0, 'rgba(0,0,0,0)'); gr.addColorStop(e1, `rgba(0,0,0,${quietAmt * 0.6})`); gr.addColorStop(e2, `rgba(0,0,0,${quietAmt})`);
      gr.addColorStop(1 - e2, `rgba(0,0,0,${quietAmt})`); gr.addColorStop(1 - e1, `rgba(0,0,0,${quietAmt * 0.6})`); gr.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.globalCompositeOperation = 'destination-out';
      ctx.fillStyle = gr; ctx.fillRect(mid - half - soft, 0, span, H);
      ctx.globalCompositeOperation = 'source-over';
    }
  }

  function loop(now) { if (running) { draw(now); requestAnimationFrame(loop); } }
  resize();
  window.addEventListener('resize', resize);
  if (reduce) { prog = progT; draw(t0 + 6000); window.addEventListener('scroll', () => { prog = progT; draw(t0 + 6000); }, { passive: true }); return; }
  document.addEventListener('visibilitychange', () => { const was = running; running = !document.hidden; if (running && !was) requestAnimationFrame(loop); });
  requestAnimationFrame(loop);
})();
