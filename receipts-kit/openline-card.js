// <openline-card> renders Point/Because/But/So with a status light.
// Accepts tiny receipt JSON OR raw OLP frames (array of SYNC/MEASURE/STITCH).

class OpenlineCard extends HTMLElement {
  static get observedAttributes() { return ["src","mode","lang-point","lang-because","lang-but","lang-so"]; }
  constructor(){ super(); this.attachShadow({mode:"open"}); this._data=null; }
  connectedCallback(){ this.#loadAndRender(); }
  attributeChangedCallback(){ this.#loadAndRender(); }

  async #loadAndRender(){
    const src=this.getAttribute("src");
    if (src) { try { this._data=await (await fetch(src,{cache:"no-store"})).json(); } catch {} }
    if (!this._data){
      const sc=this.querySelector('script[type="application/json"]');
      if (sc) { try { this._data=JSON.parse(sc.textContent); } catch {} }
    }
    if (!this._data){
      try { this._data=JSON.parse((this.textContent||"").trim()); } catch {}
    }
    if (!this._data){ return this.#renderError("No JSON found for <openline-card>."); }
    this.#render(this.#normalize(this._data));
  }

  #normalize(input){
    const toRec = (o)=>({
      point: o.claim||o.point||"—",
      because: o.because||[],
      but: o.but||[],
      so: o.so||o.therefore||"",
      telem: o.telem||{},
      threshold: (typeof o.threshold==="number")?o.threshold:0.03
    });

    if (input && (input.claim||input.point)) return this.#statusize(toRec(input));
    if (Array.isArray(input)){
      const frames=[...input].sort((a,b)=> (a.t_logical||0)-(b.t_logical||0));
      const claim=(frames.at(-1)?.nodes||[]).find(n=>n.type==="Claim")||{};
      const because=[], but=[]; let ds=null;
      for (const fr of frames){
        for (const n of (fr.nodes||[])){
          if (n.type==="Evidence") because.push(n.label||"Evidence");
          if (n.type==="Counter")  but.push(n.label||"Counter");
        }
        if (typeof fr?.telem?.delta_scale==="number") ds=fr.telem.delta_scale;
      }
      const so=this.#deriveTherefore(frames);
      return this.#statusize({ point:claim.label||"—", because, but, so, telem:{delta_scale:ds}, threshold:0.03 });
    }
    return this.#statusize({ point:"—", because:[], but:[], so:"", telem:{}, threshold:0.03 });
  }

  #deriveTherefore(frames){
    for (let i=frames.length-1;i>=0;i--){
      const fr=frames[i];
      for (const n of (fr.nodes||[])){
        if (n.type==="Evidence" && /Realized|actual|observed/i.test(n.label||"")) return n.label;
      }
    }
    const hasCounter=frames.some(fr => (fr.nodes||[]).some(n=>n.type==="Counter"));
    return hasCounter ? "Proceed with caution; see counters." : "No outstanding objections.";
  }

  #statusize(r){
    const thr = r.threshold ?? 0.03;
    const ds  = (r.telem && typeof r.telem.delta_scale==="number") ? r.telem.delta_scale : null;
    let status = "green";
    if (ds !== null){
      if (ds <= thr*0.5) status="green"; else if (ds <= thr*1.5) status="amber"; else status="red";
    } else if (r.but?.length) status="amber";
    const statusText = {green:"OK", amber:"Needs review", red:"Blocked"}[status];
    return {...r, status, statusText, threshold:thr};
  }

  #renderError(msg){
    this.shadowRoot.innerHTML = `<div role="alert" style="font:14px system-ui;padding:12px;border:1px solid #fca5a5;border-radius:8px;background:#fef2f2;color:#991b1b">${msg}</div>`;
  }

  #render(r){
    const mode=(this.getAttribute("mode")||"compact");
    const Lp=this.getAttribute("lang-point")||"Point";
    const Lb=this.getAttribute("lang-because")||"Because";
    const Lc=this.getAttribute("lang-but")||"But";
    const Ls=this.getAttribute("lang-so")||"So";
    const dot = {green:"#22c55e", amber:"#f59e0b", red:"#ef4444"}[r.status] || "#9ca3af";
    const css=`
      :host{all:initial;display:block;font:14px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
      .card{border:1px solid #e5e7eb;border-radius:12px;padding:14px 16px;background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.04)}
      .hdr{display:flex;align-items:center;gap:8px;font-weight:600;color:#111827;margin-bottom:8px}
      .dot{width:10px;height:10px;border-radius:50%;background:${dot};box-shadow:0 0 0 2px #fff inset,0 0 0 1px rgba(0,0,0,.06)}
      .status{margin-left:auto;color:#374151;font-size:12px}
      .row{display:flex;gap:10px;margin:6px 0}
      .tag{width:84px;flex:none;color:#6b7280;text-transform:uppercase;letter-spacing:.04em;font-size:11px}
      .val{color:#111827}
      .bul{margin:0;padding-left:18px}.bul li{margin:2px 0}
      details{margin-top:10px} summary{cursor:pointer;color:#374151;font-size:12px}
      code{background:#f3f4f6;padding:1px 4px;border-radius:4px}
    `;
    const ul = (arr)=> arr?.length ? `<ul class="bul">${arr.map(x=>`<li>${this.#esc(x)}</li>`).join("")}</ul>` : `<span class="val">—</span>`;
    const metrics = (typeof r?.telem?.delta_scale==="number")
      ? `<div style="color:#374151;font-size:12px;margin-top:6px">Δ_scale=<code>${r.telem.delta_scale.toFixed(3)}</code> · threshold=<code>${r.threshold.toFixed(3)}</code> · status=<code>${r.status}</code></div>` : "";

    this.shadowRoot.innerHTML = `
      <style>${css}</style>
      <div class="card" role="region" aria-label="Reasoning receipt">
        <div class="hdr"><span class="dot" aria-hidden="true"></span><span>Receipt</span><span class="status" aria-live="polite">${this.#esc(r.statusText)}</span></div>
        <div class="row"><div class="tag">${this.#esc(Lp)}</div><div class="val">${this.#esc(r.point)}</div></div>
        <div class="row"><div class="tag">${this.#esc(Lb)}</div><div class="val">${ul(r.because)}</div></div>
        <div class="row"><div class="tag">${this.#esc(Lc)}</div><div class="val">${ul(r.but)}</div></div>
        <div class="row"><div class="tag">${this.#esc(Ls)}</div><div class="val">${this.#esc(r.so||"—")}</div></div>
        ${mode==="full" ? `<details><summary>Details</summary>${metrics}</details>` : metrics}
      </div>`;
    this.dispatchEvent(new CustomEvent("openline-card:rendered",{detail:{status:r.status,telem:r.telem}}));
  }

  #esc(s){ return String(s??"").replace(/[&<>"']/g, c=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c])); }
}
customElements.define("openline-card", OpenlineCard);
