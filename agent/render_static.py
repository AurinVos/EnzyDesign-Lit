"""Build a no-network static site plus a self-contained offline HTML edition."""
from __future__ import annotations
import argparse
from collections import Counter
from html import escape
from pathlib import Path
import shutil
from .common import ROOT, read_json, validate_dataset, atomic_text, csv_export, script_json

METHODS=['Experimental screening','Bioinformatics / genome mining','Directed evolution','Machine learning','Protein language models','Structure-based design','Generative models','Active learning','Molecular simulation','Agentic workflows']
OBJECTIVES=['Discovery','Engineering','Design']

def e(value):return escape(str(value or ''),quote=True)

def card(p):
    tags=''.join(f'<span class="pill {e(v)}">{e(v)}</span>' for v in p['objectives'])
    tags+=''.join(f'<span class="pill grey">{e(v)}</span>' for v in p['enzyme_families'])
    tags+=f'<span class="pill outline">{e(p["validation"])}</span>'
    return f'''<article class="paper-card"><div class="paper-meta"><span class="year">{p['year']}</span><span>·</span><span>{e(p.get('journal'))}</span></div><h3 class="paper-title"><a href="{e(p['source_url'])}" target="_blank" rel="noopener noreferrer">{e(p['title'])}</a></h3><p class="paper-citation">{e(p.get('citation'))}</p><p class="paper-summary">{e(p.get('summary'))}</p><div class="tags">{tags}</div><div class="paper-foot"><span class="status">{e({'curated':'Source-checked seed · AI-assisted','verified':'Human-reviewed'}.get(p['status'],'Candidate'))}</span><a href="{e(p['source_url'])}" target="_blank" rel="noopener noreferrer">Original publication ↗</a></div></article>'''

def timeline(papers):
    counts=Counter(p['year'] for p in papers)
    if not counts:return '<p>No records in this view.</p>'
    first,last=min(counts),max(counts);peak=max(counts.values())
    bars=''.join(f'<div class="year-col"><span class="year-bar {"" if counts[y] else "zero"}" style="--height:{max(1,counts[y]/peak*116):.1f}px" title="{y}: {counts[y]}"><span>{counts[y] or ""}</span></span></div>' for y in range(first,last+1))
    return '<div class="year-chart" aria-label="Publication year distribution">'+bars+f'</div><div class="axis"><span>{first}</span><span>{round(first+(last-first)/3)}</span><span>{round(first+2*(last-first)/3)}</span><span>{last}</span></div>'

def matrix(papers):
    text='<table class="matrix"><caption class="visually-hidden">Paper counts by method and objective</caption><thead><tr><th scope="col">Method</th>'+''.join(f'<th scope="col">{o}</th>' for o in OBJECTIVES)+'</tr></thead><tbody>'
    for m in METHODS:
        if not any(m in p['methods'] for p in papers):continue
        cells=''.join(f'<td>{sum(m in p["methods"] and o in p["objectives"] for p in papers)}</td>' for o in OBJECTIVES)
        text+=f'<tr><th scope="row">{e(m)}</th>{cells}</tr>'
    return text+'</tbody></table>'

def render(root=ROOT):
    root=Path(root);data=read_json(root/'data/papers.json');validate_dataset(data)
    selected=[p for p in data['papers'] if p['status'] in ('curated','verified')]
    selected=sorted(selected,key=lambda p:p['published_date'],reverse=True)
    candidates=sum(p['status']=='candidate' for p in data['papers'])
    exp=sum(p['validation']=='Experimental assays reported' for p in selected)
    stats=''.join(f'<div class="stat"><strong>{value}</strong><span>{label}</span></div>' for value,label in [(len(selected),'source-checked / reviewed papers'),(exp,'papers reporting experiments'),(candidates,'candidates awaiting review'),(str(min((p['year'] for p in selected),default=0))+'–'+str(max((p['year'] for p in selected),default=0)),'publication years represented')])
    search=data['meta'].get('last_search')
    state='Live retrieval has not been run for this release. The starting papers were source-checked individually; no scheduled service is claimed to be active.' if not search else f'Last recorded search: {search["as_of"]}. '+('Query retrieval completed within configured bounds; coverage is still limited to the searched sources and queries.' if search['complete_within_queries'] else 'Incomplete retrieval: one or more result windows were capped or contained invalid records. Consult the versioned search logs.')
    release=f'<span><strong>Selected starting collection.</strong> AI-assisted source checks; not an exhaustive systematic review.</span><span>Seed checked {e(data["meta"].get("seed_checked_on","unknown"))} · {"Search log available" if search else "Live updates not yet activated"}</span>'
    replacements={'STATS':stats,'RELEASE':release,'TIMELINE':timeline(selected),'MATRIX':matrix(selected),'COUNT':f'{len(selected)} records','CARDS':'\n'.join(card(p) for p in selected),'SEARCHSTATE':e(state)}
    template=(root/'assets/template.html').read_text(encoding='utf-8')
    for marker,content in replacements.items():
        needle='<!-- '+marker+' -->'
        if template.count(needle)!=1:raise ValueError('Template marker missing or duplicated: '+marker)
        template=template.replace(needle,content)
    payload='window.ENZYME_ATLAS = '+script_json(data)+';\n'
    css=(root/'assets/styles.css').read_text(encoding='utf-8')
    js=(root/'assets/app.js').read_text(encoding='utf-8')
    index=template.replace('<!-- STYLE -->','<link rel="stylesheet" href="assets/styles.css">').replace('<!-- DATA -->','<script src="data/papers.js"></script>').replace('<!-- APP -->','<script src="assets/app.js"></script>')
    standalone=template.replace('<!-- STYLE -->','<style>'+css+'</style>').replace('<!-- DATA -->','<script>'+payload+'</script>').replace('<!-- APP -->','<script>'+js+'</script>')
    atomic_text(root/'index.html',index);atomic_text(root/'data/papers.js',payload)
    atomic_text(root/'data/papers.csv',csv_export(data['papers']))
    atomic_text(root/'Enzyme_Evidence_Atlas.html',standalone)
    site=root/'_site';site.mkdir(exist_ok=True)
    for filename in ('index.html','LICENSE','NOTICE.md'):
        path=root/filename
        if path.exists():shutil.copy2(path,site/filename)
    for folder,names in [('assets',['styles.css','app.js']),('data',['papers.js','papers.json','papers.csv'])]:
        (site/folder).mkdir(exist_ok=True)
        for name in names:shutil.copy2(root/folder/name,site/folder/name)
    atomic_text(site/'.nojekyll','')
    print(f'Built static site and self-contained HTML: {len(selected)} selected records; {candidates} candidates.')
    return data

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);a=p.parse_args();render(a.root)
if __name__=='__main__':main()
