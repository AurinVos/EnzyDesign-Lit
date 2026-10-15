"""Retrieve literature into a persistent candidate queue. Never overwrites curated labels.

Examples: python -m agent.update --provider europepmc --days 120
          python -m agent.update --input tests/fixtures/candidates.json --as-of 2026-10-15
"""
from __future__ import annotations
import argparse
import copy
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
from .common import ROOT, SCHEMA, CONFIG, read_json, write_json, validate_dataset, fingerprint
from .classify import tag_candidate, VERSION
from .providers import fetch_query, RetrievalError

def merge_records(existing: list[dict], incoming: list[dict]) -> list[dict]:
    by_id={p['id']:copy.deepcopy(p) for p in existing}
    for item in incoming:
        p=copy.deepcopy(item)
        if p['id'] in by_id:
            old=by_id[p['id']]
            # Preserve all screening decisions and curated fields. Append only provenance.
            for event in p.get('provenance',[]):
                if event not in old['provenance']: old['provenance'].append(event)
            if not old.get('abstract') and p.get('abstract'): old['abstract']=p['abstract']
            continue
        p.update(tag_candidate(p['title'],p.get('abstract','')))
        by_id[p['id']]=p
    return sorted(by_id.values(),key=lambda x:(x['published_date'],x['id']),reverse=True)

def apply_decisions(papers: list[dict], envelope: dict) -> list[dict]:
    if envelope.get('schema_version')!=SCHEMA or not isinstance(envelope.get('decisions'),list): raise ValueError('Invalid review decision file')
    result=copy.deepcopy(papers); by_id={p['id']:p for p in result}; seen=set()
    for decision in envelope['decisions']:
        rid=decision.get('id','')
        if rid not in by_id or rid in seen: raise ValueError('Unknown or duplicate review ID: '+rid)
        seen.add(rid)
        if decision.get('status') not in ('verified','excluded','candidate'): raise ValueError('Invalid review status')
        if not str(decision.get('reviewer','')).strip() or not str(decision.get('reason','')).strip(): raise ValueError('Reviewer name and reason are required')
        if decision.get('basis') not in CONFIG['review_bases']: raise ValueError('Review basis required')
        stamp=str(decision.get('reviewed_on',''))
        try: datetime.fromisoformat(stamp.replace('Z','+00:00'))
        except ValueError as exc: raise ValueError('Valid review timestamp required') from exc
        paper=by_id[rid]
        paper.setdefault('review_history',[]).append(copy.deepcopy(decision))
        paper['status']=decision['status']; paper['review']=copy.deepcopy(decision)
    return result

def year_windows(start: str,end: str):
    first=date.fromisoformat(start); last=date.fromisoformat(end)
    while first<=last:
        stop=min(last,date(first.year,12,31))
        yield first.isoformat(),stop.isoformat()
        first=stop+timedelta(days=1)

def main(argv=None):
    arg=argparse.ArgumentParser(description=__doc__)
    arg.add_argument('--root',type=Path,default=ROOT)
    arg.add_argument('--provider',choices=['europepmc','openalex','all'],default='europepmc')
    arg.add_argument('--days',type=int,default=120)
    arg.add_argument('--start-date')
    arg.add_argument('--as-of',default=date.today().isoformat())
    arg.add_argument('--max-pages',type=int,default=3)
    arg.add_argument('--page-size',type=int,default=100)
    arg.add_argument('--query-id',action='append')
    arg.add_argument('--input',type=Path,help='Import normalized provider records (offline, not a live search)')
    arg.add_argument('--decisions',type=Path)
    arg.add_argument('--dry-run',action='store_true')
    arg.add_argument('--require-complete',action='store_true')
    arg.add_argument('--llm',action='store_true',help='Optional model suggestions; never automatic inclusion')
    arg.add_argument('--llm-max-records',type=int,default=50,help='Maximum new candidates sent to the optional paid API per run')
    args=arg.parse_args(argv)
    try:
        end=date.fromisoformat(args.as_of)
        if not 1<=args.llm_max_records<=1000: raise ValueError('LLM record budget must be 1–1000')
        if args.llm and (not os.getenv('OPENAI_API_KEY') or not os.getenv('OPENAI_MODEL')): raise ValueError('--llm requires OPENAI_API_KEY and OPENAI_MODEL')
        if not 1<=args.days<=36525 or not 1<=args.max_pages<=100 or not 1<=args.page_size<=100: raise ValueError('Invalid retrieval bounds')
        start=date.fromisoformat(args.start_date) if args.start_date else end-timedelta(days=args.days)
        if start>end: raise ValueError('Start date exceeds end date')
        data_path=args.root/'data/papers.json'
        original=read_json(data_path,{'schema_version':SCHEMA,'meta':{},'papers':[]})
        validate_dataset(original)
        data=copy.deepcopy(original); reports=[]; incoming=[]
        searches=read_json(args.root/'config/searches.json',[])
        if args.query_id:
            unknown=set(args.query_id)-{q['id'] for q in searches}
            if unknown: raise ValueError('Unknown query IDs: '+','.join(unknown))
            searches=[q for q in searches if q['id'] in args.query_id]
        if args.input:
            incoming=read_json(args.input)
            if isinstance(incoming,dict): incoming=incoming['papers']
            reports=[{'provider':'offline_import','count':len(incoming),'truncated':False,'file_name':args.input.name}]
        elif not args.decisions:
            providers=['europepmc','openalex'] if args.provider=='all' else [args.provider]
            windows=list(year_windows(start.isoformat(),end.isoformat())) if args.start_date else [(start.isoformat(),end.isoformat())]
            for provider in providers:
                for left,right in windows:
                    for query in searches:
                        records,report=fetch_query(provider,query,left,right,mode='historical' if args.start_date else 'incremental',max_pages=args.max_pages,page_size=args.page_size)
                        incoming.extend(records); reports.append(report)
                        print(f'{provider}/{query["id"]}: {report["retrieved"]}/{report["reported_matches"]}, truncated={report["truncated"]}')
        if args.require_complete and any(r.get('truncated') or r.get('invalid_records') for r in reports): raise RetrievalError('Incomplete retrieval; no dataset changes committed')
        data['papers']=merge_records(data['papers'],incoming)
        if args.llm:
            from .llm import suggest
            old_ids={p['id'] for p in original['papers']}
            new=[p for p in data['papers'] if p['id'] not in old_ids]
            for p in new[:args.llm_max_records]: suggest(p)
            print(f'LLM suggestions: {min(len(new),args.llm_max_records)}/{len(new)} new records; remaining candidates retain keyword suggestions')
        if args.decisions: data['papers']=apply_decisions(data['papers'],read_json(args.decisions))
        now=datetime.now(timezone.utc).isoformat()
        report={'schema_version':SCHEMA,'run_at':now,'as_of':end.isoformat(),'run_type':'review_import' if args.decisions and not args.input else 'offline_import' if args.input else 'live_search','classifier_version':VERSION,'search_config_sha256':fingerprint(searches),'queries':reports,'new_records':len(data['papers'])-len(original['papers']),'warnings':[f'{r.get("provider")}/{r.get("query_id")}: result cap reached' for r in reports if r.get('truncated')], 'complete_within_queries':not any(r.get('truncated') or r.get('invalid_records') for r in reports)}
        data['meta']['last_operation']=report
        if not args.input and not args.decisions: data['meta']['last_search']=report
        validate_dataset(data)
        # Nothing is written until every retrieval, decision and validation succeeds.
        if not args.dry_run:
            run_name=now.replace(':','-')+'-'+report['run_type']+'.json'
            write_json(args.root/'data/search_runs'/run_name,report)
            write_json(data_path,data)
        print(json.dumps({'new_records':report['new_records'],'total':len(data['papers']),'dry_run':args.dry_run,'run_type':report['run_type']}))
        return 0
    except (ValueError,KeyError,TypeError,RetrievalError,OSError,json.JSONDecodeError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        return 1

if __name__=='__main__': raise SystemExit(main())
