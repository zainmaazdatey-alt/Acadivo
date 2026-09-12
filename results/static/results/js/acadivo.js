/* ═══════════════════════════════════════════════════════════
   ACADIVO — Main JavaScript
   Theme : Obsidian Violet (Glowed)
   Covers: Intro loader · 3D depth particles · 3D tilt ·
           Scroll reveal · Count-up · Live marks · Nav
   ═══════════════════════════════════════════════════════════ */

'use strict';

/* ══════════════════════════════════════
   1. INTRO LOADER
══════════════════════════════════════ */
function initIntroLoader() {
  const loader = document.getElementById('intro-loader');
  if (!loader) return;

  document.body.style.overflow = 'hidden';

  const logo     = loader.querySelector('.intro-logo');
  const sub      = loader.querySelector('.intro-sub');
  const progress = loader.querySelector('.intro-progress');
  const fill     = loader.querySelector('.intro-progress-fill');

  // Staggered entrance
  setTimeout(() => {
    if (logo)     logo.classList.add('show');
    if (sub)      sub.classList.add('show');
    if (progress) progress.classList.add('show');
  }, 120);

  setTimeout(() => {
    if (fill) fill.classList.add('fill');
  }, 200);

  // Fade out
  setTimeout(() => {
    loader.classList.add('hidden');
    document.body.style.overflow = '';
  }, 1900);
}

/* ══════════════════════════════════════
   2. 3D DEPTH PARTICLE SYSTEM
   Particles have a z (depth) value.
   Near (z=1): large, bright, fast, strong repel.
   Far  (z=0): tiny, dim,   slow, weak repel.
   Creates true parallax depth on scroll.
══════════════════════════════════════ */
function initParticles() {
  const canvas = document.getElementById('acadivo-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  let W, H, dots = [];
  let mouse = { x: -9999, y: -9999 };

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = Math.max(document.body.scrollHeight, window.innerHeight);
  }

  function createDots() {
    dots = [];
    const count = Math.floor((W * H) / 14000);
    for (let i = 0; i < count; i++) {
      const z = Math.random(); // depth 0=far, 1=near
      dots.push({
        x:     Math.random() * W,
        y:     Math.random() * H,
        z,
        vx:    (Math.random() - 0.5) * (0.1 + z * 0.3),
        vy:    (Math.random() - 0.5) * (0.1 + z * 0.3),
        r:     0.3 + z * 1.8,
        alpha: 0.04 + z * 0.32,
        pulse: Math.random() * Math.PI * 2,
        // Near dots are pure violet, far ones lean lavender
        color: Math.random() < 0.35 ? '191,163,255' : '157,111,255',
      });
    }
  }

  function drawFrame() {
    ctx.clearRect(0, 0, W, H);
    const now = Date.now() / 1000;
    const sy  = window.scrollY;

    dots.forEach(d => {
      // Move
      d.x += d.vx;
      d.y += d.vy;
      if (d.x < 0 || d.x > W) d.vx *= -1;
      if (d.y < 0 || d.y > H) d.vy *= -1;

      // Parallax: near dots move more with scroll
      const drawY = d.y - sy * (0.05 + d.z * 0.12);

      // Mouse repel — stronger for near dots
      const mx   = d.x - mouse.x;
      const my   = drawY - (mouse.y - sy);
      const dist = Math.sqrt(mx * mx + my * my);
      const maxR = 80 + d.z * 60;
      if (dist < maxR && dist > 0) {
        const force = ((maxR - dist) / maxR) * (0.5 + d.z * 1.5);
        d.x += (mx / dist) * force;
        d.y += (my / dist) * force;
      }

      // Pulse alpha
      const pulse = Math.sin(now * 1.2 + d.pulse) * 0.25 + 0.75;
      const wrappedY = ((drawY % H) + H) % H;

      ctx.beginPath();
      ctx.arc(d.x, wrappedY, d.r * pulse, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${d.color},${(d.alpha * pulse).toFixed(3)})`;
      ctx.fill();
    });

    // Draw connection lines — only between similar-depth dots
    for (let i = 0; i < dots.length; i++) {
      for (let j = i + 1; j < dots.length; j++) {
        if (Math.abs(dots[i].z - dots[j].z) > 0.35) continue;

        const yA = ((dots[i].y - sy * (0.05 + dots[i].z * 0.12)) % H + H) % H;
        const yB = ((dots[j].y - sy * (0.05 + dots[j].z * 0.12)) % H + H) % H;
        const dx = dots[i].x - dots[j].x;
        const dy = yA - yB;
        const d2 = Math.sqrt(dx * dx + dy * dy);
        const maxD = 90 + dots[i].z * 40;

        if (d2 < maxD) {
          const avgZ = (dots[i].z + dots[j].z) / 2;
          const a    = ((1 - d2 / maxD) * 0.15 * avgZ).toFixed(3);
          ctx.beginPath();
          ctx.moveTo(dots[i].x, yA);
          ctx.lineTo(dots[j].x, yB);
          ctx.strokeStyle = `rgba(157,111,255,${a})`;
          ctx.lineWidth   = 0.4 + avgZ * 0.4;
          ctx.stroke();
        }
      }
    }

    requestAnimationFrame(drawFrame);
  }

  window.addEventListener('mousemove', e => {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
  });
  window.addEventListener('resize', () => { resize(); createDots(); });
  document.fonts.ready.then(() => { resize(); createDots(); drawFrame(); });
}

/* ══════════════════════════════════════
   3. 3D CARD TILT
   Attach to any element with .tilt-card
══════════════════════════════════════ */
function initTilt() {
  document.querySelectorAll('.tilt-card').forEach(el => {
    let raf;
    el.addEventListener('mousemove', e => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const r = el.getBoundingClientRect();
        const x = (e.clientX - r.left)  / r.width  - 0.5;
        const y = (e.clientY - r.top)   / r.height - 0.5;
        el.style.transform = `perspective(1400px) rotateY(${x * 4}deg) rotateX(${-y * 3}deg) scale(1.003)`;
        el.style.transition = 'transform 0.22s ease-out';
      });
    });
    el.addEventListener('mouseleave', () => {
      cancelAnimationFrame(raf);
      el.style.transition = 'transform 0.7s cubic-bezier(0.22,1,0.36,1)';
      el.style.transform  = '';
    });
  });
}

/* ══════════════════════════════════════
   4. SCROLL REVEAL
   All .reveal elements fade up when
   they enter the viewport.
══════════════════════════════════════ */
function initScrollReveal() {
  const obs = new IntersectionObserver(entries => {
    entries.forEach((e, i) => {
      if (e.isIntersecting) {
        setTimeout(() => e.target.classList.add('visible'), i * 50);
        obs.unobserve(e.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

  document.querySelectorAll('.reveal').forEach(el => obs.observe(el));

  // Shimmer on cards when they enter viewport
  const shimmerObs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('shimmer-in');
        shimmerObs.unobserve(e.target);
      }
    });
  }, { threshold: 0.06 });

  document.querySelectorAll('.tilt-card, .login-page').forEach(el => shimmerObs.observe(el));
}

/* ══════════════════════════════════════
   5. COUNT-UP ANIMATION
   countUpEl(el, target, duration, decimals)
══════════════════════════════════════ */
function countUpEl(el, to, ms, dec = 1) {
  const start = performance.now();
  function step(now) {
    const p    = Math.min((now - start) / ms, 1);
    const ease = 1 - Math.pow(1 - p, 3);
    el.textContent = (ease * to).toFixed(dec);
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function initCountUps() {
  // CGPA — student dashboard
  const cgpaEl = document.getElementById('cgpa-value');
  if (cgpaEl) {
    const target = parseFloat(cgpaEl.dataset.value || 0);
    const obs = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          countUpEl(cgpaEl, target, 1400, 1);
          obs.disconnect();
        }
      });
    }, { threshold: 0.5 });
    obs.observe(cgpaEl);
  }

  // Stat cards — admin dashboard
  document.querySelectorAll('[data-count]').forEach(el => {
    const to  = parseFloat(el.dataset.count);
    const dec = el.dataset.dec !== undefined ? parseInt(el.dataset.dec) : 0;
    const ms  = parseInt(el.dataset.ms || 900);
    const obs = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          countUpEl(el, to, ms, dec);
          obs.disconnect();
        }
      });
    }, { threshold: 0.6 });
    obs.observe(el);
  });
}

/* ══════════════════════════════════════
   6. NAV HIGHLIGHT
   Sticky nav link becomes active based
   on scroll position.
══════════════════════════════════════ */
function initNavHighlight() {
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('.sidebar-item[data-section]');
  if (!sections.length || !navLinks.length) return;

  window.addEventListener('scroll', () => {
    let current = '';
    sections.forEach(s => {
      if (window.scrollY >= s.offsetTop - 100) current = s.id;
    });
    navLinks.forEach(a => {
      a.classList.toggle('active', a.dataset.section === current);
    });
  }, { passive: true });
}

/* ══════════════════════════════════════
   7. LIVE MARK CALCULATION
   Called oninput on mark entry inputs.
   Calculates total, %, grade in real time.
══════════════════════════════════════ */
const GRADE_SCALE = [
  [90, 'O',  'badge-O',  10],
  [75, 'A+', 'badge-Ap',  9],
  [65, 'A',  'badge-A',   8],
  [55, 'B+', 'badge-Bp',  7],
  [50, 'B',  'badge-B',   6],
  [40, 'C',  'badge-C',   5],
  [0,  'F',  'badge-F',   0],
];

function getGrade(pct) {
  for (const [min, grade, cls, gp] of GRADE_SCALE) {
    if (pct >= min) return { grade, cls, gp };
  }
  return { grade: 'F', cls: 'badge-F', gp: 0 };
}

window.calcMarks = function(input) {
  const row  = input.closest('tr');
  if (!row) return;
  const inputs = row.querySelectorAll('.mark-input');
  const ceMax  = parseInt(row.dataset.ceMax  || 20);
  const eseMax = parseInt(row.dataset.eseMax || 30);

  const ce  = Math.min(ceMax,  Math.max(0, parseFloat(inputs[0]?.value) || 0));
  const ese = Math.min(eseMax, Math.max(0, parseFloat(inputs[1]?.value) || 0));
  const tot = ce + ese;
  const pct = Math.round((tot / (ceMax + eseMax)) * 100);
  const { grade, cls, gp } = getGrade(pct);

  const totEl   = row.querySelector('.mark-total');
  const pctEl   = row.querySelector('.mark-pct');
  const gradeEl = row.querySelector('.mark-grade');
  const gpEl    = row.querySelector('.mark-gp');

  if (totEl)   totEl.textContent   = tot;
  if (pctEl)   pctEl.textContent   = pct + '%';
  if (gradeEl) gradeEl.innerHTML   = `<span class="badge ${cls}">${grade}</span>`;
  if (gpEl)    gpEl.textContent    = gp;
};

/* ══════════════════════════════════════
   8. ROLE SWITCH (login page)
══════════════════════════════════════ */
window.switchRole = function(el) {
  el.closest('.role-switch').querySelectorAll('.role-option').forEach(o => o.classList.remove('active'));
  el.classList.add('active');

  // Update hidden input so Django knows which role
  const roleInput = document.getElementById('role-input');
  if (roleInput) roleInput.value = el.dataset.role;
};

/* ══════════════════════════════════════
   9. SEM TABS (student dashboard)
══════════════════════════════════════ */
window.switchSemTab = function(el, semNum) {
  // Update tabs UI
  el.closest('.sem-tabs').querySelectorAll('.sem-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');

  // Show/hide result panels
  document.querySelectorAll('.sem-panel').forEach(p => {
    p.style.display = p.dataset.sem === String(semNum) ? 'block' : 'none';
  });
};

/* ══════════════════════════════════════
   10. SIDEBAR ITEM ACTIVE STATE
══════════════════════════════════════ */
function initSidebarActive() {
  // Mark current page's sidebar item as active based on URL
  const path = window.location.pathname;
  document.querySelectorAll('.sidebar-item[href]').forEach(link => {
    if (link.getAttribute('href') === path) link.classList.add('active');
  });
}

/* ══════════════════════════════════════
   11. DJANGO MESSAGES AUTO-DISMISS
      (success/error alerts)
══════════════════════════════════════ */
function initMessages() {
  document.querySelectorAll('.alert[data-autohide]').forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity 0.4s ease';
      alert.style.opacity = '0';
      setTimeout(() => alert.remove(), 400);
    }, 4000);
  });
}

/* ══════════════════════════════════════
   12. CSV UPLOAD — filename display
══════════════════════════════════════ */
function initCSVUpload() {
  const fileInput = document.getElementById('csv-file-input');
  const fileLabel = document.getElementById('csv-file-label');
  if (!fileInput || !fileLabel) return;

  fileInput.addEventListener('change', () => {
    const name = fileInput.files[0]?.name || 'No file chosen';
    fileLabel.textContent = name;
  });
}

/* ══════════════════════════════════════
   INIT ALL ON DOM READY
══════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  initIntroLoader();
  initParticles();
  initTilt();
  initScrollReveal();
  initCountUps();
  initNavHighlight();
  initSidebarActive();
  initMessages();
  initCSVUpload();
});

/* ══════════════════════════════════════
   STEP 12 — FINAL POLISH JS
══════════════════════════════════════ */

/* ── Auto-dismiss Django messages after 4s ── */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.alert[data-autohide]').forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      el.style.opacity    = '0';
      el.style.transform  = 'translateY(-6px)';
      setTimeout(() => el.remove(), 400);
    }, 4000);
  });
});

/* ── Progress bar widths animated on scroll ── */
(function() {
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        const bar  = e.target;
        const pct  = bar.dataset.pct;
        if (pct) bar.style.width = pct + '%';
        obs.unobserve(bar);
      }
    });
  }, { threshold: 0.3 });
  document.querySelectorAll('.progress-fill[data-pct]').forEach(el => {
    el.style.width = '0%';
    obs.observe(el);
  });
})();

/* ── Mark input: clamp value on blur ── */
document.addEventListener('blur', e => {
  const inp = e.target;
  if (!inp.classList.contains('mark-input')) return;
  const min = parseFloat(inp.min) || 0;
  const max = parseFloat(inp.max);
  let   val = parseFloat(inp.value);
  if (isNaN(val)) return;
  if (val < min) inp.value = min;
  if (max && val > max) inp.value = max;
}, true);

/* ── Topbar scroll shadow ── */
window.addEventListener('scroll', () => {
  const tb = document.querySelector('.topbar');
  if (tb) tb.style.boxShadow = window.scrollY > 10
    ? '0 2px 20px rgba(0,0,0,0.4)'
    : 'none';
}, { passive: true });

/* ── Table row click highlight (preview tables) ── */
document.querySelectorAll('.acadivo-table tbody tr').forEach(tr => {
  tr.addEventListener('click', function() {
    this.closest('tbody').querySelectorAll('tr')
        .forEach(r => r.classList.remove('highlight'));
    this.classList.add('highlight');
  });
});
