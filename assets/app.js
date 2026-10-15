/* Enzyme Evidence Atlas — MIT. Credit to Bas van der Velden in NOTICE.md. */
(() => {
  'use strict';
  const data = window.ENZYME_ATLAS;
  if (!data || !Array.isArray(data.papers)) return;
  document.documentElement.classList.add('js');
  const $ = id => document.getElementById(id);
  const fields = ['objectives','methods','enzyme_families','validation','sequence_space','year'];
  const objectives = ['Discovery','Engineering','Design'];
  const matrixMethods = ['Experimental screening','Bioinformatics / genome mining','Directed evolution','Machine learning','Protein language models','Structure-based design','Generative models','Active learning','Molecular simulation','Agentic workflows'];
  const shortMethod = {'Bioinformatics / genome mining':'Sequence / genome mining','Experimental screening':'Experimental screening','Protein language models':'Protein language models','Structure-based design':'Structure-based design'};
  const state = {status:'selected',objectives:'',methods:'',enzyme_families:'',validation:'',sequence_space:'',year:'',search:'',sort:'newest',tab:'all',limit:12};
  const key = 'enzyme-evidence-atlas-v1';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const safeUrl = raw => {try {const u = new URL(raw); return ['https:','http:'].includes(u.protocol) && !u.username && !u.password ? u.href : '';} catch (_) {return '';}};
  const link = (url,label,cls='') => safeUrl(url) ? `<a class="${esc(cls)}" href="${esc(safeUrl(url))}" target="_blank" rel="noopener noreferrer">${esc(label)}</a>` : esc(label);
  const unique = (items) => [...new Set(items)];
  const readLocal = (suffix,fallback) => {try {return JSON.parse(localStorage.getItem(key+suffix)) ?? fallback;} catch(_){return fallback;}};
  const writeLocal = (suffix,obj) => {try {localStorage.setItem(key+suffix,JSON.stringify(obj));return true;} catch(_){toast('Browser storage is unavailable. Export your decisions before closing.');return false;}};
  let rawSaved=readLocal('-saved',[]);
  const saved = new Set(Array.isArray(rawSaved)?rawSaved.filter(x=>typeof x==='string'):[]);
  let reviews = readLocal('-reviews',{});
  if (!reviews || typeof reviews!=='object' || Array.isArray(reviews)) reviews={};
  let openId = null, lastFocus=null, toastTimer;
  const isReview = p => /review|perspective/i.test(p.record_type||'') || p.validation==='Review / perspective';
  const statusLabel = p => ({curated:'Source-checked seed · AI-assisted',verified:'Human-reviewed',candidate:'Automated candidate',excluded:'Excluded · audit record'}[p.status]||'Unassessed');
  const displayDate = p => p.date_precision==='year' ? p.published_date : p.date_precision==='month' ? p.published_date : p.published_date;
  const pill = (value,extra='') => `<span class="pill ${esc(extra)}">${esc(value)}</span>`;
  function toast(message) {$('toast').textContent=message;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,4000);}
  function filtered() {
    const query=state.search.toLocaleLowerCase().trim();
    let rows=data.papers.filter(p=> {
      if(state.status==='selected' && !['curated','verified'].includes(p.status))return false;
      if(state.status==='all' && p.status==='excluded')return false;
      if(!['selected','all'].includes(state.status) && p.status!==state.status)return false;
      if(fields.some(f=>state[f] && !(Array.isArray(p[f])?p[f].includes(state[f]):String(p[f])===state[f])))return false;
      if(state.tab==='review'&&!isReview(p))return false;
      if(state.tab==='research'&&isReview(p))return false;
      if(state.tab==='saved'&&!saved.has(p.id))return false;
      if(query && ![p.title,p.summary,p.abstract,p.citation,p.journal,p.doi,p.validation,p.sequence_space,...(p.objectives||[]),...(p.methods||[]),...(p.enzyme_families||[])].join(' ').toLocaleLowerCase().includes(query))return false;
      return true;
    });
    rows.sort((a,b)=>state.sort==='title'?a.title.localeCompare(b.title):state.sort==='oldest'?a.published_date.localeCompare(b.published_date):b.published_date.localeCompare(a.published_date));
    return rows;
  }
  function card(p) {
    return `<article class="paper-card" data-paper-id="${esc(p.id)}"><div class="paper-meta"><span class="year">${esc(p.year)}</span><span aria-hidden="true">·</span><span>${esc(p.journal||'Source not supplied')}</span>${isReview(p)?pill('Review','outline'):''}</div><h3 class="paper-title"><button data-open="${esc(p.id)}">${esc(p.title)}</button></h3><p class="paper-citation">${esc(p.citation||'See original publication for author details')}</p><p class="paper-summary">${esc(p.summary||'Candidate identified from bibliographic metadata; scientific relevance has not been reviewed.')}</p><div class="tags">${(p.objectives||[]).map(o=>pill(o,o)).join('')}${(p.enzyme_families||[]).map(f=>pill(f,'grey')).join('')}${pill(p.validation,'outline')}</div><div class="paper-foot"><span class="status">${esc(statusLabel(p))}${reviews[p.id]?' · local review draft':''}</span><button class="save" data-save="${esc(p.id)}" aria-pressed="${saved.has(p.id)}" aria-label="${saved.has(p.id)?'Remove from':'Add to'} shortlist: ${esc(p.title)}">${saved.has(p.id)?'★':'☆'}</button><button class="text-button" data-open="${esc(p.id)}">Evidence</button>${link(p.source_url,'Publication ↗')}</div></article>`;
  }
  function renderList() {
    const rows=filtered();$('paper-list').innerHTML=rows.slice(0,state.limit).map(card).join('');
    $('results-count').textContent=`${rows.length} ${rows.length===1?'record':'records'}`;
    $('empty-state').hidden=rows.length>0;$('show-more').hidden=rows.length<=state.limit;
    $('show-more').textContent=`Show ${Math.min(12,rows.length-state.limit)} more (${Math.max(0,rows.length-state.limit)} remaining)`;
    $('saved-count').textContent=saved.size;
    document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.tab===state.tab)));
    $('active-filters').innerHTML=fields.filter(f=>state[f]).map(f=>`<button class="pill outline" data-clear="${esc(f)}" aria-label="Remove filter ${esc(state[f])}">${esc(state[f])} ×</button>`).join('');
    renderCharts(rows);
  }
  function renderCharts(rows) {
    const allYears=data.papers.filter(p=>p.status!=='excluded').map(p=>p.year);
    const first=allYears.length?Math.min(...allYears):new Date().getFullYear(),last=allYears.length?Math.max(...allYears):first;
    const counts=new Map();rows.forEach(p=>counts.set(p.year,(counts.get(p.year)||0)+1));
    const max=Math.max(1,...counts.values());
    let bars='';for(let y=first;y<=last;y++){const n=counts.get(y)||0;bars+=`<div class="year-col"><button class="year-bar ${n?'':'zero'}" style="--height:${Math.max(1,n/max*116)}px" data-year="${y}" aria-label="${y}: ${n} records. Filter to ${y}." title="${y}: ${n} records"><span>${n||''}</span></button></div>`;}
    $('timeline').innerHTML=`<div class="year-chart" role="group" aria-label="Publication counts, ${first} to ${last}">${bars}</div><div class="axis"><span>${first}</span><span>${Math.round(first+(last-first)/3)}</span><span>${Math.round(first+2*(last-first)/3)}</span><span>${last}</span></div>`;
    const methods=matrixMethods.filter(m=>data.papers.some(p=>(p.methods||[]).includes(m)));
    $('matrix').innerHTML=`<table class="matrix"><caption class="visually-hidden">Number of filtered papers with both each method and objective</caption><thead><tr><th scope="col">Method</th>${objectives.map(o=>`<th scope="col">${o}</th>`).join('')}</tr></thead><tbody>${methods.map(m=>`<tr><th scope="row">${esc(shortMethod[m]||m)}</th>${objectives.map(o=>{const n=rows.filter(p=>(p.methods||[]).includes(m)&&(p.objectives||[]).includes(o)).length;return `<td><button class="${n?'nonzero':''}" data-matrix-method="${esc(m)}" data-matrix-objective="${o}" aria-label="${esc(m)} and ${o}: ${n} records">${n}</button></td>`;}).join('')}</tr>`).join('')}</tbody></table>`;
    $('chart-scope').textContent=`${rows.length} currently filtered ${rows.length===1?'record':'records'}. These are collection counts, not estimates of research-field prevalence.`;
  }
  function populateFilters() {
    for(const f of fields){const values=unique(data.papers.flatMap(p=>Array.isArray(p[f])?p[f]:[p[f]]).filter(v=>v!==undefined&&v!==null));values.sort((a,b)=>f==='year'?Number(b)-Number(a):String(a).localeCompare(String(b)));for(const v of values){const option=document.createElement('option');option.value=v;option.textContent=v;$('filter-'+f).appendChild(option);}$('filter-'+f).addEventListener('change',e=>{state[f]=e.target.value;state.limit=12;renderList();});}
    $('filter-status').addEventListener('change',e=>{state.status=e.target.value;state.limit=12;renderList();});
  }
  function reset() {
    Object.assign(state,{status:'selected',objectives:'',methods:'',enzyme_families:'',validation:'',sequence_space:'',year:'',search:'',sort:'newest',tab:'all',limit:12});
    fields.forEach(f=>$('filter-'+f).value='');$('filter-status').value='selected';$('search').value='';$('sort').value='newest';renderList();
  }
  function detail(id) {
    const p=data.papers.find(p=>p.id===id);if(!p)return;
    openId=id;lastFocus=document.activeElement;
    const draft=reviews[id]||{};
    const option=(value,label,current)=>`<option value="${esc(value)}" ${value===current?'selected':''}>${esc(label)}</option>`;
    $('detail-content').innerHTML=`<div class="paper-meta"><span>${esc(displayDate(p))}</span><span>· ${esc(p.journal)}</span>${pill(statusLabel(p),'outline')}</div><h2 id="detail-title">${esc(p.title)}</h2><p>${esc(p.citation||'Author metadata available at source')}${p.authors_complete===false?' · Abbreviated attribution; consult the publication for the full author list.':''}</p><p>${esc(p.summary||'No reviewed summary is available for this candidate.')}</p><div class="exports">${link(p.source_url,'Original publication ↗','button primary')}${p.doi?link('https://doi.org/'+p.doi,'DOI: '+p.doi,'button'):''}</div><div class="detail-grid"><div><small>Research objectives</small><strong>${esc((p.objectives||[]).join(' · ')||'Not assigned')}</strong></div><div><small>Methods</small><strong>${esc((p.methods||[]).join(' · ')||'Not assigned')}</strong></div><div><small>Sequence space</small><strong>${esc(p.sequence_space)}</strong></div><div><small>Evidence type</small><strong>${esc(p.validation)}</strong></div><div><small>Enzyme family / group</small><strong>${esc((p.enzyme_families||[]).join(' · ')||'Not assigned')}</strong></div><div><small>Publication date</small><strong>${esc(p.published_date)} (${esc(p.date_precision)} precision)${p.issue_year?`; issue year ${esc(p.issue_year)}`:''}</strong></div></div><h3>What the evidence supports</h3><p>${esc(p.evidence_note||'Evidence has not been assessed. Follow the publication before drawing scientific conclusions.')}</p><h3>Classification and provenance</h3><p>${esc(p.classification?.method||'No classification method recorded')} · ${esc(p.classification?.basis||'Basis not recorded')}. ${esc(p.classification?.note||'')}</p><p>${esc(p.date_note||'Date supplied by the bibliographic source.')} Source check: ${esc(p.checked_on||'Not source-checked')}.</p><div>${(p.provenance||[]).map(v=>`<p>${link(v.url,v.source+' ↗')}${v.accessed_on?' · accessed '+esc(v.accessed_on):''}${v.basis?' · '+esc(v.basis):''}</p>`).join('')}</div>${(p.resource_links||[]).length?'<h3>Linked research resources</h3><p>'+p.resource_links.map(v=>link(v.url,v.label+' ('+v.kind+')')).join(' · ')+'</p>':''}${(p.related_ids||[]).length?'<h3>Related versions / identifiers</h3><p>'+p.related_ids.map(x=>x.startsWith('doi:')?link('https://doi.org/'+x.slice(4),x):esc(x)).join('<br>')+'</p>':''}${p.abstract?'<details><summary>Provider abstract</summary><p>'+esc(p.abstract)+'</p></details>':''}${p.review?'<h3>Recorded human decision</h3><p>'+esc(p.review.reviewer)+' · '+esc(p.review.basis)+' · '+esc(p.review.reviewed_on)+'<br>'+esc(p.review.reason)+'</p>':''}<details class="review-box"><summary>Record a local review decision</summary><p>This draft is saved only in this browser. It changes the published collection only after export, validated import and rebuild. Do not use “Human-reviewed” to imply full-text checking when only an abstract was read.</p><form id="review-form"><div class="review-grid"><div><label for="reviewer">Reviewer name</label><input id="reviewer" name="reviewer" required maxlength="120" value="${esc(draft.reviewer||'')}" autocomplete="name"></div><div><label for="review-status">Decision</label><select id="review-status" name="status">${option('candidate','Needs further review',draft.status||'candidate')}${option('verified','Include: human-reviewed',draft.status)}${option('excluded','Exclude from evidence map',draft.status)}</select></div></div><label for="review-basis">Material actually reviewed</label><select id="review-basis" name="basis">${option('title_abstract','Title and abstract',draft.basis||'title_abstract')}${option('full_text','Full text',draft.basis)}</select><label for="review-reason">Decision reason / limitations</label><textarea id="review-reason" name="reason" required maxlength="3000">${esc(draft.reason||'')}</textarea><div class="exports" style="margin-top:12px"><button class="button primary" type="submit">Save local decision</button><button class="button" type="button" id="discard-review">Discard local draft</button></div></form><p class="review-notice" id="review-message">${draft.id?'A local draft exists for this record.':''}</p></details>`;
    $('review-form').addEventListener('submit',e=>{e.preventDefault();const form=new FormData(e.target);const reviewer=String(form.get('reviewer')||'').trim(),reason=String(form.get('reason')||'').trim();if(!reviewer||!reason){toast('A reviewer name and reason are required.');return;}reviews[id]={id,status:String(form.get('status')),basis:String(form.get('basis')),reviewer,reason,reviewed_on:new Date().toISOString()};const persisted=writeLocal('-reviews',reviews);$('review-message').textContent=persisted?'Draft saved locally. Export review decisions to update the repository.':'Draft held in memory only. Export before closing.';renderList();});
    $('discard-review').addEventListener('click',()=>{delete reviews[id];writeLocal('-reviews',reviews);$('review-message').textContent='Local draft removed.';renderList();});
    if(!$('paper-dialog').open)$('paper-dialog').showModal();$('close-dialog').focus();
  }
  function download(content,mime,filename) {const blob=new Blob([content],{type:mime});const url=URL.createObjectURL(blob);const anchor=document.createElement('a');anchor.href=url;anchor.download=filename;document.body.appendChild(anchor);anchor.click();anchor.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);}
  const csvCell=value=>{let s=Array.isArray(value)?value.join('; '):String(value??'');if(/^\s*[=+@-]/.test(s)||/^[\t\r\n]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';};
  const tex = value => String(value??'').replace(/[\\{}%&#_$]/g,c=>({'\\':'\\textbackslash{}','{':'\\{','}':'\\}','%':'\\%','&':'\\&','#':'\\#','_':'\\_','$':'\\$'}[c]));
  function exportData(format) {
    const rows=filtered();
    if(format==='json'){download(JSON.stringify({schema_version:data.schema_version,meta:{...data.meta,export:{filtered:true,filters:{...state},exported_on:new Date().toISOString()}},papers:rows},null,2),'application/json','enzyme-evidence-filtered.json');}
    if(format==='csv'){const cols=['id','title','year','published_date','date_precision','citation','journal','doi','objectives','methods','enzyme_families','sequence_space','validation','status','summary','source_url','checked_on'];download('\uFEFF'+[cols.map(csvCell).join(','),...rows.map(p=>cols.map(c=>csvCell(p[c])).join(','))].join('\r\n'),'text/csv;charset=utf-8','enzyme-evidence-filtered.csv');}
    if(format==='bib'){const text=rows.map((p,i)=>{const entry=p.record_type==='Preprint'?'misc':'article';return `@${entry}{enzyme${p.year}_${i+1},\n  title = {${tex(p.title)}},\n  journal = {${tex(p.journal||'')}},\n  year = {${p.year}},\n${p.doi?'  doi = {'+tex(p.doi)+'},\n':''}  url = {${tex(p.source_url)}},\n  note = {${tex('Abbreviated attribution: '+(p.citation||'see publication')+'. Full author metadata must be completed from the original publication before manuscript submission.')}}\n}`;}).join('\n\n');download(text+'\n','application/x-bibtex;charset=utf-8','enzyme-evidence-filtered.bib');}
    toast(`Exported ${rows.length} filtered records.`);
  }
  function exportReviews(){const decisions=Object.values(reviews);download(JSON.stringify({schema_version:data.schema_version,exported_on:new Date().toISOString(),decisions},null,2)+'\n','application/json','review-decisions.json');toast(`Exported ${decisions.length} local review decisions.`);}
  document.addEventListener('click',e=>{
    const target=e.target.closest('button');if(!target)return;
    if(target.dataset.open){detail(target.dataset.open);return;}
    if(target.dataset.save){const id=target.dataset.save;if(saved.has(id))saved.delete(id);else saved.add(id);writeLocal('-saved',[...saved]);renderList();return;}
    if(target.dataset.tab){state.tab=target.dataset.tab;state.limit=12;renderList();return;}
    if(target.dataset.clear){const f=target.dataset.clear;state[f]='';$('filter-'+f).value='';state.limit=12;renderList();return;}
    if(target.dataset.year){state.year=target.dataset.year;$('filter-year').value=state.year;state.limit=12;renderList();$('explore').scrollIntoView();return;}
    if(target.dataset.matrixMethod){state.methods=target.dataset.matrixMethod;state.objectives=target.dataset.matrixObjective;$('filter-methods').value=state.methods;$('filter-objectives').value=state.objectives;state.limit=12;renderList();$('explore').scrollIntoView();return;}
    if(target.dataset.export)exportData(target.dataset.export);
  });
  $('search').addEventListener('input',e=>{state.search=e.target.value;state.limit=12;renderList();});
  $('sort').addEventListener('change',e=>{state.sort=e.target.value;renderList();});
  $('show-more').addEventListener('click',()=>{state.limit+=12;renderList();});
  $('reset-filters').addEventListener('click',reset);$('empty-reset').addEventListener('click',reset);
  $('close-dialog').addEventListener('click',()=>$('paper-dialog').close());
  $('paper-dialog').addEventListener('close',()=>{openId=null;if(lastFocus?.isConnected)lastFocus.focus();});
  $('paper-dialog').addEventListener('click',e=>{if(e.target===$('paper-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
  $('export-reviews').addEventListener('click',exportReviews);
  if(readLocal('-theme','light')==='dark')document.body.classList.add('dark');
  $('theme-toggle').addEventListener('click',()=>{document.body.classList.toggle('dark');writeLocal('-theme',document.body.classList.contains('dark')?'dark':'light');});
  document.addEventListener('keydown',e=>{if(e.key==='/'&&!$('paper-dialog').open&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('search').focus();}});
  populateFilters();renderList();
})();
