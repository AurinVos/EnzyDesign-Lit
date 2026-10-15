"""Europe PMC and OpenAlex adapters, using Python standard library only.

Official contracts: https://europepmc.org/RestfulWebService
https://help.openalex.org/api/  (consulted 2026-10-15).
"""
from __future__ import annotations
from datetime import date
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from .common import normalize_doi, abstract_from_index, canonical_id, strip_html, validate_record

class RetrievalError(RuntimeError): pass

def http_json(url: str, *, headers=None, payload=None, attempts=4):
    data=None if payload is None else json.dumps(payload).encode()
    req=Request(url,data=data,headers={'User-Agent':'EnzymeEvidenceAtlas/1.0 (literature metadata research)','Accept':'application/json', **({'Content-Type':'application/json'} if data else {}), **(headers or {})})
    for i in range(attempts):
        try:
            with urlopen(req, timeout=40) as response:
                if int(response.headers.get('Content-Length','0'))>25_000_000: raise RetrievalError('Oversized response')
                body=response.read(25_000_001)
                if len(body)>25_000_000: raise RetrievalError('Oversized response')
                return json.loads(body)
        except HTTPError as exc:
            if exc.code not in (429,500,502,503,504) or i==attempts-1: raise RetrievalError(f'HTTP {exc.code}; API key, allowance or service may need attention') from exc
            retry=exc.headers.get('Retry-After','')
            time.sleep(min(float(retry),60) if retry.isdigit() else min(2**i,30))
        except (URLError, TimeoutError) as exc:
            if i==attempts-1: raise RetrievalError('Network request failed; existing collection is unchanged') from exc
            time.sleep(2**i)
    raise RetrievalError('Retry budget exhausted')

def _base(title, doi, source, source_id, date_value, authors, journal, abstract, source_url, today):
    published=str(date_value or '')
    import re
    if not re.fullmatch(r'\d{4}(?:-\d{2}(?:-\d{2})?)?',published): raise ValueError('Missing/invalid date in source record')
    parts=published.split('-')
    earliest=date(int(parts[0]),int(parts[1]) if len(parts)>1 else 1,int(parts[2]) if len(parts)>2 else 1)
    if earliest>date.fromisoformat(today): raise ValueError('Future publication date')
    if not title: raise ValueError('Missing title')
    doi=normalize_doi(doi)
    return {'id':canonical_id(doi,source,source_id),'doi':doi,'title':strip_html(title),
      'year':int(published[:4]),'published_date':published,'date_precision':{4:'year',7:'month',10:'day'}[len(published)],
      'citation':authors or 'Author details at source','journal':journal or 'Source not specified',
      'abstract':strip_html(abstract),'summary':'Retrieved bibliographic candidate; relevance and findings require review.',
      'source_url':source_url,'first_seen':today,'checked_on':'','record_type':'Research / type not assessed',
      'provenance':[{'source':source,'id':str(source_id),'url':source_url,'retrieved_on':today,'basis':'provider_metadata'}],
      'resource_links':[],'related_ids':[],'targets':[],
      'objectives':[],'methods':[],'enzyme_families':[],'sequence_space':'Not assessed','validation':'Not assessed','status':'candidate', 'evidence_note':'Experimental validation has not been assessed.'}

def normalize_epmc(work: dict, today: str) -> dict:
    source=work.get('source','MED'); sid=str(work.get('id',''))
    if not sid: raise ValueError('Missing Europe PMC stable ID')
    doi=normalize_doi(work.get('doi'))
    journal=(((work.get('journalInfo') or {}).get('journal') or {}).get('title') or work.get('journalTitle',''))
    p=_base(work.get('title',''),doi,'Europe PMC '+source,sid,work.get('firstPublicationDate') or work.get('pubYear'),work.get('authorString',''),journal,work.get('abstractText',''),f'https://europepmc.org/article/{quote(source,safe="")}/{quote(sid,safe="")}',today)
    types=(work.get('pubTypeList') or {}).get('pubType') or []
    if not isinstance(types,list) or any(not isinstance(t,str) for t in types): raise ValueError('Invalid publication type list')
    p['record_type']='Preprint' if source=='PPR' or any('preprint' in t.lower() for t in types) else 'Review' if any('review' in t.lower() for t in types) else 'Research article'
    p['provider_types']=types
    p['first_index_date']=work.get('firstIndexDate','')
    p['provenance'][0]['date_note']='Europe PMC firstPublicationDate can contain provider-normalized dates; date precision is source-reported, not independently verified.'
    return p

def normalize_openalex(w: dict,today: str) -> dict:
    doi=normalize_doi(w.get('doi'))
    sid=w.get('id','')
    if not sid: raise ValueError('Missing OpenAlex ID')
    authors='; '.join(a.get('author',{}).get('display_name','') for a in w.get('authorships',[]) if a.get('author',{}).get('display_name'))
    p=_base(w.get('title',''),doi,'OpenAlex',sid.rsplit('/',1)[-1],w.get('publication_date') or str(w.get('publication_year') or ''),authors,(w.get('primary_location') or {}).get('source',{}).get('display_name','') if (w.get('primary_location') or {}).get('source') else '',abstract_from_index(w.get('abstract_inverted_index')),sid,today)
    p['record_type']='Preprint' if w.get('type')=='preprint' else 'Review' if w.get('type')=='review' else 'Research article'
    p['provenance'][0]['date_note']='OpenAlex publication date; provider metadata, not independent first-version verification.'
    return p

def build_epmc_query(term: str,start: str,end: str,mode: str='incremental') -> str:
    window=f'FIRST_PDATE:[{start} TO {end}]'
    if mode=='incremental': window=f'({window} OR FIRST_IDATE:[{start} TO {end}])'
    return f'({term}) AND {window} AND FIRST_PDATE:[1800-01-01 TO {end}]'

def fetch_query(provider: str, query: dict,start: str,end: str,*,mode='incremental',max_pages=3,page_size=100,client=http_json) -> tuple[list[dict],dict]:
    if provider not in ('europepmc','openalex'): raise ValueError('Unknown provider')
    if not 1<=page_size<=100 or not 1<=max_pages<=100: raise ValueError('Invalid page budget')
    records=[]; invalid=[]; cursor='*'; total=0; retrieved=0; pages=0
    if provider=='openalex' and not os.getenv('OPENALEX_API_KEY'): raise RetrievalError('OpenAlex pagination needs OPENALEX_API_KEY; Europe PMC works without a key')
    term=build_epmc_query(query[provider],start,end,mode) if provider=='europepmc' else query[provider]
    for _ in range(max_pages):
        if provider=='europepmc':
            params={'query':term,'format':'json','resultType':'core','pageSize':page_size,'cursorMark':cursor}
            base='https://www.ebi.ac.uk/europepmc/webservices/rest/search'
            js=client(base+'?'+urlencode(params))
            if 'hitCount' not in js or 'resultList' not in js: raise RetrievalError('Unexpected Europe PMC response; not a successful empty search')
            batch=js['resultList'].get('result',[]); total=int(js['hitCount']); next_cursor=js.get('nextCursorMark')
            normalizer=normalize_epmc
        else:
            params={'search':term,'filter':f'from_publication_date:{start},to_publication_date:{end}','per_page':page_size,'cursor':cursor}
            base='https://api.openalex.org/works'
            js=client(base+'?'+urlencode(params),headers={'Authorization':'Bearer '+os.environ['OPENALEX_API_KEY']})
            if 'results' not in js or 'meta' not in js: raise RetrievalError('Unexpected OpenAlex response')
            batch=js['results']; total=int(js['meta']['count']); next_cursor=js['meta'].get('next_cursor'); normalizer=normalize_openalex
        if not isinstance(batch,list) or total<0: raise RetrievalError('Invalid result list or result count')
        pages+=1; retrieved+=len(batch)
        for work in batch:
            if not isinstance(work,dict):
                invalid.append({'source_id':'unknown','reason':'Non-object source record'})
                continue
            try:
                p=normalizer(work,end)
                p['provenance'][0]['query_id']=query['id']
                p['first_seen']=date.today().isoformat()
                p['provenance'][0]['retrieved_on']=date.today().isoformat()
                validate_record(p)
                records.append(p)
            except (ValueError,TypeError,KeyError) as exc:
                invalid.append({'source_id':str(work.get('id','')),'reason':str(exc)})
        if not batch or retrieved>=total or not next_cursor or next_cursor==cursor: break
        cursor=next_cursor
        time.sleep(0.2)
    report={'provider':provider,'query_id':query['id'],'query':term,'from':start,'to':end,'mode':mode,'pages':pages,'reported_matches':total,'retrieved':retrieved,'normalized':len(records),'truncated':retrieved<total,'invalid_records':invalid}
    if provider=='openalex' and mode=='incremental': report['limitation']='Publication-date lookback only; delayed indexing outside this window requires historical reconciliation.'
    return records,report
