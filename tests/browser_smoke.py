#!/usr/bin/env python3
"""Browser checks; run after the build.

Normal mode serves the real files over localhost and uses real origin storage.
--content-mode is an explicitly limited fallback for environments that prohibit
all navigation: injects the standalone HTML and emulates localStorage. This mode
checks rendering, interactions and serialized exports, NOT network delivery or
native browser storage persistence. It never bypasses navigation restrictions.
"""
from __future__ import annotations
import argparse
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
import json
from pathlib import Path
import shutil
import sys
from threading import Thread
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--content-mode',action='store_true');ap.add_argument('--chromium');args=ap.parse_args()
    report={'mode':'injected_standalone_with_emulated_storage' if args.content_mode else 'localhost_real_origin','checks':[],'javascript_errors':[],'navigation_tested':not args.content_mode,'native_storage_tested':not args.content_mode}
    def check(label,condition):
        if not condition:raise AssertionError(label)
        report['checks'].append(label)
        print('PASS: '+label,flush=True)
    html=(ROOT/'Enzyme_Evidence_Atlas.html').read_text(encoding='utf-8')
    data=json.loads((ROOT/'data/papers.json').read_text());selected=[p for p in data['papers'] if p['status'] in ('curated','verified')]
    server=None
    if not args.content_mode:
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)))
        Thread(target=server.serve_forever,daemon=True).start()
    with sync_playwright() as p:
        opts={'headless':True}
        executable=args.chromium or shutil.which('chromium')
        if executable:opts['executable_path']=executable
        browser=p.chromium.launch(**opts)
        context=browser.new_context(viewport={'width':1440,'height':1080},accept_downloads=True)
        page=context.new_page();page.set_default_timeout(7000);page.on('pageerror',lambda e:report['javascript_errors'].append(str(e)))
        if args.content_mode:
            page.evaluate('''() => {const store={};window.__testStore=store;Object.defineProperty(window,'localStorage',{configurable:true,value:{getItem:k=>store[k]??null,setItem:(k,v)=>{store[k]=String(v)},removeItem:k=>delete store[k]}});}''')
            load=lambda:page.set_content(html)
        else:load=lambda:page.goto(f'http://127.0.0.1:{server.server_port}/Enzyme_Evidence_Atlas.html')
        load()
        check('Initial JavaScript render',page.locator('.paper-card').count()==min(12,len(selected)))
        check('Derived selected count',page.locator('#results-count').inner_text()==f'{len(selected)} records')
        check('Visible upstream attribution',page.get_by_text('Bas van der Velden',exact=True).count()>=1)
        check('Desktop has no horizontal overflow',not page.evaluate('document.documentElement.scrollWidth>innerWidth'))
        page.screenshot(path=str(ROOT/'reports/desktop-preview.png'),full_page=False)
        while page.locator('#show-more').is_visible():page.locator('#show-more').click()
        check('Pagination reaches final paper',page.locator('.paper-card').count()==len(selected))
        page.locator('#search').fill('Durairaj')
        check('Author search filters correctly',page.locator('.paper-card').count()==1 and 'sesquiterpene' in page.locator('.paper-title').inner_text())
        page.locator('#reset-filters').click();page.locator('#filter-objectives').select_option('Discovery')
        expected=sum('Discovery' in r['objectives'] for r in selected)
        check('Objective filter count',page.locator('#results-count').inner_text()==f'{expected} records')
        page.locator('#filter-sequence_space').select_option('De novo / generated')
        check('Discovery allows generated sequence space',page.locator('.paper-card').count()>=1)
        page.locator('#reset-filters').click();page.locator('[data-tab="review"]').click()
        check('Review and primary studies separated',page.locator('.paper-card').count()==1 and 'Machine-learning-guided' in page.locator('.paper-title').inner_text())
        page.locator('#reset-filters').click();page.locator('#filter-status').select_option('candidate')
        check('Empty candidate queue is explicit',page.locator('#empty-state').is_visible())
        page.locator('#empty-reset').click();page.locator('#sort').select_option('oldest')
        check('Oldest-first sort', 'subtilisin' in page.locator('.paper-title').first.inner_text())
        page.locator('#reset-filters').click();page.locator('[data-year="2023"]').click()
        check('Timeline bar click filters',page.locator('#filter-year').input_value()=='2023')
        check('Timeline count matches records',page.locator('.paper-card').count()==sum(r['year']==2023 for r in selected))
        page.locator('#reset-filters').click();page.locator('[data-matrix-method="Protein language models"][data-matrix-objective="Design"]').click()
        check('Matrix intersection filters both axes',page.locator('#filter-objectives').input_value()=='Design' and page.locator('#filter-methods').input_value()=='Protein language models')
        check('Matrix returns correct intersection',page.locator('.paper-card').count()==sum('Design' in r['objectives'] and 'Protein language models' in r['methods'] for r in selected))
        page.locator('#reset-filters').click();page.locator('[data-save]').first.click();page.locator('[data-tab="saved"]').click()
        check('Shortlist adds record',page.locator('.paper-card').count()==1)
        load();page.locator('[data-tab="saved"]').click()
        check('Shortlist restored from storage adapter',page.locator('.paper-card').count()==1)
        page.locator('#reset-filters').click();page.locator('.paper-title button').first.click()
        check('Details dialog opens',page.locator('#paper-dialog').evaluate('(el)=>el.open'))
        check('Evidence qualifications present','not a direct activity predictor' in page.locator('#detail-content').inner_text())
        page.locator('.review-box summary').click()
        check('Reviewer is required',page.locator('#reviewer').evaluate('(el)=>el.required'))
        page.locator('#reviewer').fill('Browser fixture reviewer');page.locator('#review-reason').fill('Synthetic browser test only. Not a scientific review.')
        page.locator('#review-status').select_option('verified');page.locator('#review-basis').select_option('title_abstract')
        page.locator('#review-form button[type="submit"]').click()
        check('Review draft saved', 'Draft saved locally' in page.locator('#review-message').inner_text())
        page.locator('#close-dialog').click()
        check('Local draft does not mutate published status',page.evaluate('window.ENZYME_ATLAS.papers[0].status')=='curated')
        # Capture actual generated Blob contents. The click is suppressed only at
        # the download anchor, so tests do not require an allowed download policy.
        page.evaluate('''() => {window.__exports=[];const create=URL.createObjectURL.bind(URL);URL.createObjectURL=b=>{window.__exports.push(b);return create(b)};document.addEventListener('click',e=>{if(e.target.closest('a[download]'))e.preventDefault()},true);}''')
        page.locator('#export-reviews').click();exported=page.evaluate('async()=>JSON.parse(await window.__exports.at(-1).text())')
        check('Review JSON matches importer schema',exported['schema_version']=='1.0.0' and len(exported['decisions'])==1 and exported['decisions'][0]['reviewer']=='Browser fixture reviewer')
        page.locator('#search').fill('Durairaj');page.locator('[data-export="json"]').click();exported=page.evaluate('async()=>JSON.parse(await window.__exports.at(-1).text())')
        check('JSON export respects current filters',len(exported['papers'])==1 and 'Durairaj' in exported['papers'][0]['citation'])
        check('JSON export keeps provenance','provenance' in exported['papers'][0])
        page.locator('[data-export="csv"]').click();csv=page.evaluate('async()=>await window.__exports.at(-1).text()')
        check('CSV export includes DOI and title','10.1371/journal.pcbi.1008197' in csv and 'Integrating structure-based' in csv)
        page.locator('[data-export="bib"]').click();bib=page.evaluate('async()=>await window.__exports.at(-1).text()')
        check('BibTeX discloses incomplete authors','Full author metadata must be completed' in bib and '10.1371/journal.pcbi.1008197' in bib)
        page.locator('#reset-filters').click();page.locator('#theme-toggle').click()
        check('Dark theme toggles',page.locator('body').evaluate('(el)=>el.classList.contains("dark")'))
        page.locator('#theme-toggle').click()
        page.locator('#explore').scroll_into_view_if_needed();page.screenshot(path=str(ROOT/'reports/explorer-preview.png'),full_page=False)
        for width in [390,320]:
            page.set_viewport_size({'width':width,'height':844});page.evaluate('scrollTo(0,0)')
            check(f'Mobile {width}px has no horizontal overflow',not page.evaluate('document.documentElement.scrollWidth>innerWidth'))
            if width==390:page.screenshot(path=str(ROOT/'reports/mobile-preview.png'),full_page=False)
        page.locator('.paper-title button').first.click()
        check('Mobile dialog fits viewport',page.locator('#paper-dialog').bounding_box()['width']<=320)
        page.keyboard.press('Escape');check('Escape closes modal',not page.locator('#paper-dialog').evaluate('(el)=>el.open'))
        check('No JavaScript exceptions',not report['javascript_errors'])
        nojs=browser.new_context(java_script_enabled=False);plain=nojs.new_page()
        if args.content_mode:plain.set_content(html)
        else:plain.goto(f'http://127.0.0.1:{server.server_port}/Enzyme_Evidence_Atlas.html')
        check('No-JavaScript snapshot lists all selected papers',plain.locator('.paper-card').count()==len(selected))
        check('No-JavaScript attribution retained','Bas van der Velden' in plain.locator('body').inner_text())
        browser.close()
    if server:server.shutdown()
    report['passed']=len(report['checks']);report['export_file_transfer_tested']=False
    (ROOT/'reports/browser-smoke.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
