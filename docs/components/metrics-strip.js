<!-- docs/components/metrics-strip.js -->
<script>
(function(){
  const el = document.createElement('div');
  el.className = 'tile';
  el.innerHTML = `
    <div class="muted">Coherence Signals</div>
    <div class="small">κ <b id="kappa">—</b> · Δhol <b id="dhol">—</b> · C <b id="cycles">—</b> · X <b id="xfront">—</b></div>
    <div class="small"><span id="status" class="tag">—</span></div>`;
  (document.querySelector('.grid')||document.body).appendChild(el);

  function band(v,min,ok){ return v>min?'warn':(v>ok?'warn':'ok'); }

  fetch('./receipt.latest.json?'+Date.now()).then(r=>r.json()).then(j=>{
    const t = (j.temporal && j.temporal.latest) || {};
    const n = (j.narrative && j.narrative.continuity) || {};
    const k = t.kappa ?? null, dh = t.delta_hol ?? null, C = n.cycles_C ?? 0, X = n.contradictions_X ?? 0;

    const set = (id,v)=>{const x=document.getElementById(id); if(x) x.textContent=(v==null?'—':v);};
    set('kappa', k?.toFixed?.(3));
    set('dhol', dh?.toFixed?.(3));
    set('cycles', C);
    set('xfront', X);

    const s = document.getElementById('status');
    const red = (dh>0.50) || (X>7) || (C>4);
    const amber = (k>0.70) || (X>=3) || (C>=2);
    s.textContent = red ? 'BLOCK' : (amber ? 'WARN' : 'PASS');
    s.style.background = red ? '#7f1d1d' : (amber ? '#a16207' : '#14532d');
  }).catch(()=>{});
})();
</script>
<style>
.tag{display:inline-block;padding:.2em .6em;border-radius:6px;background:#3f3f46;color:#fff}
.tile{border:1px solid #e5e7eb;border-radius:10px;padding:10px;margin:8px 0}
.muted{color:#6b7280}
.small{color:#1f2937;font-size:.9rem}
</style>
