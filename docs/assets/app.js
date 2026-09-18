/* Operator notebook only. This script never crawls or simulates SearchStax results. */
'use strict';
(() => {
  const BASE = new URL('../', document.currentScript.src);
  const STORE = 'studio5864-notebook-v1';
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const url = path => new URL(path.replace(/^\/+/, ''), BASE).href;
  let data, page = 0, activeCase = null, toastTimer;
  let notebook = {meta:{},records:{}};
  try { const saved = JSON.parse(localStorage.getItem(STORE)); if (saved && saved.records) notebook = saved; } catch (_) { /* Storage can be disabled. */ }
  function save() { try { localStorage.setItem(STORE, JSON.stringify(notebook)); } catch (_) { toast('Browser storage is unavailable. Export this run to keep your evidence.'); } }
  function toast(message) { $('toast').textContent = message; $('toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').hidden = true, 4400); }
  function meta() { return {run_label:$('run-id').value.trim() || 'Run-001',environment:$('environment').value,ignore_robots_txt:$('ignore-robots').value==='on',crawl_run_id:$('crawl-id').value.trim(),phase:data.build_phase}; }
  function key(c) { const m=meta(); return JSON.stringify([m.run_label,m.environment,m.ignore_robots_txt,m.phase,c.id]); }
  function record(c) { return notebook.records[key(c)] || {result:'Not run',actual:'',evidence:''}; }
  function expected(c) { return $('ignore-robots').value==='on' ? c.expected_on : c.expected_off; }
  const yn = value => value===true ? 'Yes' : value===false ? 'No' : 'Decision / phase-specific';
  const badgeClass = gate => gate==='Ready' ? 'green' : gate==='Lifecycle' ? 'purple' : 'amber';
  function resultChip(result) { return `<span class="chip ${result==='Passed'?'green':result==='Failed'?'red':result==='Blocked'?'amber':''}">${esc(result)}</span>`; }
  async function copy(text) { try { await navigator.clipboard.writeText(text); toast('Copied: '+text); } catch (_) { window.prompt('Copy this value:',text); } }
  function download(name, content, mime) { const a=document.createElement('a'); const object=URL.createObjectURL(new Blob([content],{type:mime})); a.href=object; a.download=name; document.body.appendChild(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(object),1000); }
  function stats() { const records=data.cases.map(record); const recorded=records.filter(r=>r.result!=='Not run').length; $('stat-recorded').textContent=recorded; const passed=records.filter(r=>r.result==='Passed').length; const failed=records.filter(r=>r.result==='Failed').length; $('result-summary').textContent=recorded ? `${passed} passed / ${failed} failed / ${data.case_count-recorded} not run` : 'Actual crawler results, entered manually'; }
  function changeTab(tab) {
    document.querySelectorAll('.tab-content').forEach(el=>el.hidden=el.id!=='tab-'+tab);
    document.querySelectorAll('[data-tab]').forEach(el=>{const active=el.dataset.tab===tab;el.classList.toggle('active',active);if(active)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current');});
    if(tab==='catalog')renderTable();
  }
  function renderSuites() {
    const icons={core:'{}',meta:'<>',links:'->',headers:'HTTP',robots:'TXT',bots:'UA',decisions:'?'};
    $('suite-grid').innerHTML=data.suites.filter(s=>s.slug!=='decisions').map(s=>`<section class="panel suite-card"><div class="suite-card-top"><span class="suite-icon">${esc(icons[s.slug])}</span><span class="chip ${s.slug==='bots'?'amber':''}">${s.count} cases</span></div><h3>${esc(s.title)}</h3><p>${esc(s.description)}</p><button class="btn small" data-copy-seed="${esc(s.url)}">Copy crawl seed &rarr;</button></section>`).join('');
    $('suite-grid').querySelectorAll('[data-copy-seed]').forEach(button=>button.addEventListener('click',()=>copy(url(button.dataset.copySeed))));
  }
  function filtered() { const q=$('search').value.trim().toLowerCase(),g=$('group-filter').value,r=$('gate-filter').value;return data.cases.filter(c=>(!g||c.group===g)&&(!r||c.gate===r)&&(!q||[c.id,c.title,c.note,c.raw_head,JSON.stringify(c.headers)].join(' ').toLowerCase().includes(q))); }
  function renderTable() {
    if(!data)return;
    const list=filtered(),size=12;page=Math.max(0,Math.min(page,Math.max(0,Math.ceil(list.length/size)-1)));
    $('case-rows').innerHTML=list.slice(page*size,(page+1)*size).map(c=>{
      const e=expected(c),indexText=e.parent_index===true?'Index allowed':e.parent_index===false?'Do not index':'Pending decision';
      return `<tr><td class="case-id">${c.id}</td><td class="case-title">${esc(c.title)}<small>${esc(c.group)}</small></td><td><span class="chip ${e.parent_index===false?'purple':''}">${indexText}</span></td><td><span class="chip ${badgeClass(c.gate)}">${c.gate}</span></td><td>${resultChip(record(c).result)}</td><td><button class="btn small" data-case="${c.id}" aria-label="View case ${c.id}">View &rarr;</button></td></tr>`;
    }).join('') || '<tr><td colspan="6" class="empty-state">No cases match these filters.</td></tr>';
    $('case-rows').querySelectorAll('[data-case]').forEach(button=>button.addEventListener('click',()=>openCase(button.dataset.case)));
    $('page-label').textContent=list.length ? `${page*size+1}-${Math.min((page+1)*size,list.length)} of ${list.length} cases` : '0 cases';
    $('prev').disabled=page===0;$('next').disabled=(page+1)*size>=list.length;
  }
  function renderDecisions() {
    $('decision-grid').innerHTML=data.cases.filter(c=>c.gate==='Confirm').map(c=>`<section class="panel decision-card"><div class="eyebrow">${c.id} / ${esc(c.group)}</div><h3>${esc(c.title)}</h3><p>${esc(c.note)}</p><button class="btn small" data-case="${c.id}">Inspect fixture &rarr;</button></section>`).join('');
    $('decision-grid').querySelectorAll('[data-case]').forEach(button=>button.addEventListener('click',()=>openCase(button.dataset.case)));
  }
  function openCase(id) {
    const c=data.cases.find(x=>x.id===id); if(!c)return; activeCase=c;
    const e=expected(c),r=record(c),m=meta();
    $('detail-id').textContent=c.id+' / '+c.group;
    const requirements = c.requires.length ? c.requires.join(', ') : 'Static HTML only';
    const botWarning = c.requires.includes('bot-token')&&!data.bot_mapping_confirmed ? `<div class="notice"><span class="notice-symbol">!</span><div><strong>Bot token is not confirmed</strong><p><code>${esc(data.bot_meta_name)}</code> is a placeholder. Expected bot-specific behavior is conditional, not a validated product configuration.</p></div></div>` : '';
    $('detail-body').innerHTML=`<h2 id="detail-title">${esc(c.title)}</h2><div class="fixture-chips"><span class="chip ${badgeClass(c.gate)}">${c.gate}</span><span class="chip">Ignore robots.txt ${m.ignore_robots_txt?'ON':'OFF'}</span><span class="chip">${esc(data.build_phase)}</span></div><p class="muted">${esc(c.note||'Verify the independent indexing and link-discovery decisions against the actual crawl output.')}</p>${botWarning}<p class="small muted"><b>Prerequisites:</b> ${esc(requirements)}</p>
      <div class="panel"><span class="field-label">START URL - DO NOT SEED TARGETS</span><pre><code>${esc(url(c.seed))}</code></pre><div class="dialog-actions" style="margin-top:13px"><button class="btn primary small" id="copy-case">Copy start URL</button><button class="btn small" id="open-fixture">Open parent fixture</button><button class="btn small" id="check-http">Check live GET headers</button></div><p class="small muted" style="margin-top:12px;margin-bottom:0">Browser fixture checks are tester requests, not crawler execution. Keep them outside the crawler evidence time window.</p><div id="http-output" class="http-result" aria-live="polite"></div></div>
      <div class="signal-grid"><div class="signal"><span>PARENT FETCH / PROCESS</span><strong>${yn(e.parent_fetch)}</strong></div><div class="signal"><span>PARENT INDEX / UPDATE</span><strong>${yn(e.parent_index)}</strong></div></div>
      <div class="panel"><span class="field-label">PARENT MARKER</span><code>${esc(c.marker)}</code><h3>HTML head fixture</h3><pre><code>${esc(c.raw_head||'(No robots meta tag in head)')}</code></pre>${c.raw_body?`<h3>Body-only fixture</h3><pre><code>${esc(c.raw_body)}</code></pre>`:''}<h3>Required response header</h3><pre><code>${esc(c.headers.map(([n,v])=>n+': '+v).join('\n')||'(No robots response header on the parent)')}</code></pre></div>
      <h3>Isolated target expectations</h3><p class="small muted">These apply to discovery from this case only, with fresh state. Lifecycle cases may retain older documents. Eligible means not blocked by these directives; other crawl limits must not interfere.</p><div class="table-wrap"><table class="detail-table"><thead><tr><th>Target path / marker</th><th>Fetch eligible</th><th>Index expected</th></tr></thead><tbody>${e.targets.map(t=>`<tr><td><code>${esc(t.url)}</code><br><code>${esc(t.marker)}</code></td><td>${yn(t.fetch)}</td><td>${yn(t.index)}</td></tr>`).join('')}</tbody></table></div>
      <form class="note-form" id="evidence-form"><h3>Record actual crawler evidence</h3><p class="small muted">Nothing is marked Passed by this dashboard. Enter observations only after executing SearchStax.</p><label class="field-label" for="actual-status">ACTUAL RESULT</label><select class="form-input" id="actual-status">${['Not run','Passed','Failed','Blocked'].map(v=>`<option${r.result===v?' selected':''}>${v}</option>`).join('')}</select><label class="field-label" for="actual-notes">OBSERVED RESULT / PRODUCT DECISION, IF NEEDED</label><textarea class="form-input" id="actual-notes" placeholder="Parent processing, indexed marker/version, target queue provenance, and actual behavior...">${esc(r.actual)}</textarea><label class="field-label" for="evidence-ref">EVIDENCE REFERENCES</label><input class="form-input" id="evidence-ref" value="${esc(r.evidence)}" placeholder="App ID, definition/run IDs, log links, index query and timestamps"><button class="btn primary" type="submit">Save observation</button></form>`;
    $('copy-case').addEventListener('click',()=>copy(url(c.seed)));
    $('open-fixture').addEventListener('click',()=>window.open(url(c.parent),'_blank','noopener,noreferrer'));
    $('check-http').addEventListener('click',()=>checkHttp(c));
    $('evidence-form').addEventListener('submit',event=>{event.preventDefault();const status=$('actual-status').value,actual=$('actual-notes').value.trim();if(status!=='Not run'&&!actual){toast('Add an observed result before recording a verdict.');return;}if(status==='Passed'&&c.requires.includes('bot-token')&&!data.bot_mapping_confirmed){toast('Confirm and rebuild the bot-token configuration before marking this case Passed.');return;}if(status==='Passed'&&c.gate==='Confirm'&&!actual.toLowerCase().includes('decision')){toast('Record the agreed product decision in the notes before grading this case.');return;}notebook.records[key(c)]={...meta(),case_id:c.id,result:status,actual,evidence:$('evidence-ref').value.trim(),saved_at:new Date().toISOString()};save();stats();renderTable();toast('Observation saved for '+c.id);});
    if(!$('case-dialog').open)$('case-dialog').showModal();
  }
  async function checkHttp(c) {
    const button=$('check-http'),output=$('http-output');button.disabled=true;output.textContent='Inspecting the fixture response; this is not a crawler test...';
    const pages=data.pages.filter(p=>p.case_id===c.id&&(p.role==='parent'||p.headers.length||p.kind==='text'));
    const results=[];
    for(const p of pages){
      try{
        const response=await fetch(url(p.url),{cache:'no-store',redirect:'follow'});
        const actual=response.headers.get('x-robots-tag');
        const want=p.headers.filter(([n])=>n.toLowerCase()==='x-robots-tag').map(([,v])=>v).join(', ')||null;
        const normalize=v=>(v||'').toLowerCase().replace(/\s+/g,' ').replace(/\s*,\s*/g,',').trim();
        const okay=response.status===200&&normalize(actual)===normalize(want);
        await response.arrayBuffer();
        results.push(`<p><b>${okay?'Fixture header matches':'Fixture mismatch - do not grade the crawler yet'}</b><br><code>${esc(p.url)}</code><br>HTTP ${response.status}; expected X-Robots-Tag: <code>${esc(want??'(absent)')}</code>; actual: <code>${esc(actual??'(absent)')}</code><br><span class="muted">Final URL: ${esc(response.url)}</span></p>`);
      }catch(error){results.push(`<p class="warning-text">${esc(p.url)}: ${esc(error.message)}</p>`);}
    }
    if(activeCase?.id===c.id){output.innerHTML='<h3>HTTP fixture evidence only</h3>'+results.join('')+'<p class="muted">This check does not inspect indexing or crawl queues. Fetch APIs combine repeated headers; use the CLI verifier with --require-repeated for the physical-field variant.</p>';button.disabled=false;}
  }
  async function init() {
    if(location.protocol==='file:')throw new Error('Serve the site over HTTP: run python3 tools/serve.py --port 8000, then open http://localhost:8000/. Opening index.html as a file cannot load the test manifest reliably.');
    const response=await fetch(url('/assets/manifest.json'),{cache:'no-store'});if(!response.ok)throw new Error('Cannot load manifest.json (HTTP '+response.status+'). Verify the publish directory is docs/.');data=await response.json();
    if(notebook.meta){for(const [id,k]of [['run-id','run_label'],['environment','environment'],['crawl-id','crawl_run_id']])if(notebook.meta[k])$(id).value=notebook.meta[k];if(typeof notebook.meta.ignore_robots_txt==='boolean')$('ignore-robots').value=notebook.meta.ignore_robots_txt?'on':'off';}
    $('stat-total').textContent=data.case_count;$('stat-ready').textContent=data.gate_counts.Ready;$('stat-confirm').textContent=data.gate_counts.Confirm;$('nav-count').textContent=data.case_count;$('decision-count').textContent=data.gate_counts.Confirm;$('phase-label').textContent=data.build_phase.toUpperCase()+' / '+data.version;$('url-count').textContent=data.fixture_url_count+' fixture URLs';
    $('bot-summary').textContent=`Current meta-name: ${data.bot_meta_name}. Mapping confirmed: ${data.bot_mapping_confirmed?'Yes':'No - placeholder only'}. Recorded HTTP User-Agent: ${data.crawler_http_user_agent}.`;
    [...new Set(data.cases.map(c=>c.group))].forEach(group=>{const o=document.createElement('option');o.value=group;o.textContent=group;$('group-filter').appendChild(o);});
    document.querySelectorAll('[data-tab]').forEach(button=>button.addEventListener('click',()=>changeTab(button.dataset.tab)));
    for(const id of ['run-id','environment','ignore-robots','crawl-id'])$(id).addEventListener('change',()=>{notebook.meta=meta();save();stats();renderTable();});
    for(const id of ['search','group-filter','gate-filter'])$(id).addEventListener(id==='search'?'input':'change',()=>{page=0;renderTable();});
    $('prev').addEventListener('click',()=>{page--;renderTable();});$('next').addEventListener('click',()=>{page++;renderTable();});
    $('close-dialog').addEventListener('click',()=>$('case-dialog').close());
    $('export-results').addEventListener('click',()=>download('STUDIO-5864-run-evidence.json',JSON.stringify({ticket:data.ticket,exported_at:new Date().toISOString(),site_base:BASE.href,bot_meta_name:data.bot_meta_name,bot_mapping_confirmed:data.bot_mapping_confirmed,...meta(),records:data.cases.map(c=>({case_id:c.id,title:c.title,gate:c.gate,...record(c)}))},null,2),'application/json'));
    $('download-tests').addEventListener('click',async()=>{try{const r=await fetch(url('/assets/testrail-cases.csv'));if(!r.ok)throw new Error('CSV unavailable');download('STUDIO-5864-TestRail-Cases.csv','\ufeff'+await r.text(),'text/csv;charset=utf-8');}catch(e){toast(e.message);}});
    renderSuites();renderDecisions();renderTable();stats();
  }
  init().catch(error=>{$('load-error').textContent=error.message;$('load-error').hidden=false;});
})();
