"""Shared validation and serialization. MIT; upstream credit in NOTICE.md.

The static JSON/JavaScript publishing pattern, DOI normalization and
abstract-index reconstruction are adapted from Bas van der Velden's project.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'config/project.json').read_text(encoding='utf-8'))
SCHEMA = '1.0.0'

def normalize_doi(value: str | None) -> str:
    doi = unquote(str(value or '').strip())
    doi = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', doi, flags=re.I)
    return doi.lower().strip()

def abstract_from_index(index: dict | None) -> str:
    pairs = [(int(pos), word) for word, positions in (index or {}).items() for pos in positions]
    return ' '.join(word for _, word in sorted(pairs))

def strip_html(text: str | None) -> str:
    from html import unescape
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]*>', ' ', str(text or '')))).strip()

def safe_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in ('https', 'http') or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError('Expected a public HTTP(S) URL')
    return value

def canonical_id(doi: str = '', source: str = '', source_id: str = '') -> str:
    if doi:
        return 'doi:' + normalize_doi(doi)
    if source and source_id:
        return source.lower().replace(' ', '') + ':' + str(source_id)
    raise ValueError('A DOI or stable source identifier is required; title hashes are not identifiers')

def read_json(path: Path, default=None):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as handle:
            handle.write(text)
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)

def write_json(path: Path, obj) -> None:
    atomic_text(path, json.dumps(obj, ensure_ascii=False, indent=2) + '\n')

def script_json(obj) -> str:
    # Escaping '<' prevents </script>, comments and HTML parser escapes.
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')

def fingerprint(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def csv_cell(value) -> str:
    if isinstance(value, list): value = '; '.join(str(x) for x in value)
    text = str(value if value is not None else '')
    # Neutralize spreadsheet formula injection, including leading whitespace.
    if re.match(r'^\s*[=+@-]', text) or text.startswith(('\t', '\r', '\n')): text = "'" + text
    return text

def csv_export(papers: list[dict]) -> str:
    cols = ['id','title','year','published_date','date_precision','citation','journal','doi','objectives','methods','enzyme_families','sequence_space','validation','status','summary','source_url','checked_on']
    out = io.StringIO(newline='')
    writer = csv.writer(out)
    writer.writerow(cols)
    for p in papers: writer.writerow([csv_cell(p.get(c)) for c in cols])
    return out.getvalue()

def validate_record(p: dict) -> None:
    required = ['id','title','year','published_date','date_precision','doi','objectives','methods','enzyme_families','sequence_space','validation','status','source_url','provenance']
    for key in required:
        if key not in p: raise ValueError(f'Missing {key} in {p.get("id", "record")}')
    if not isinstance(p['title'], str) or not p['title'].strip(): raise ValueError('Empty title')
    if not isinstance(p['id'], str) or ':' not in p['id']: raise ValueError('Invalid stable ID')
    if type(p['year']) is not int or not 1800 <= p['year'] <= 2100: raise ValueError('Invalid publication year')
    if not re.fullmatch(r'\d{4}(?:-\d{2}(?:-\d{2})?)?', p['published_date']): raise ValueError('Invalid date precision')
    if int(p['published_date'][:4]) != p['year']: raise ValueError('Year differs from publication date')
    from datetime import date
    bits = p['published_date'].split('-')
    date(int(bits[0]), int(bits[1]) if len(bits)>1 else 1, int(bits[2]) if len(bits)>2 else 1)
    if p['date_precision'] != {1:'year', 2:'month', 3:'day'}[len(bits)]: raise ValueError('Date precision label mismatch')
    if p['doi'] and (not re.fullmatch(r'10\.\d{4,9}/\S+', p['doi']) or p['doi'] != normalize_doi(p['doi'])):
        raise ValueError('Invalid or non-normalized DOI')
    if p['doi'] and p['id'] != 'doi:' + p['doi']: raise ValueError('DOI and ID differ')
    for key, allowed in [('objectives', list(CONFIG['objectives'])), ('methods',CONFIG['methods'])]:
        if not isinstance(p[key], list) or any(v not in allowed for v in p[key]) or len(set(p[key]))!=len(p[key]): raise ValueError(f'Invalid {key}')
    if not isinstance(p['enzyme_families'], list) or any(not isinstance(x,str) for x in p['enzyme_families']): raise ValueError('Invalid enzyme families')
    for key, allowed in [('status',CONFIG['review_statuses']),('sequence_space',CONFIG['sequence_spaces']),('validation',CONFIG['validation_levels'])]:
        if p[key] not in allowed: raise ValueError(f'Invalid {key}: {p[key]}')
    safe_url(p['source_url'])
    if not isinstance(p['provenance'], list) or not p['provenance']: raise ValueError('Missing provenance')
    for item in p['provenance']:
        if not isinstance(item,dict) or not item.get('source') or not item.get('url'): raise ValueError('Incomplete provenance')
        safe_url(item['url'])
    if p['status']=='verified':
        review=p.get('review',{})
        if not review.get('reviewer') or not review.get('reason') or review.get('basis') not in CONFIG['review_bases']: raise ValueError('Reviewed record lacks human review metadata')

def validate_dataset(data: dict) -> None:
    if data.get('schema_version') != SCHEMA: raise ValueError('Unsupported schema version')
    seen=set()
    for p in data.get('papers',[]):
        validate_record(p)
        if p['id'] in seen: raise ValueError('Duplicate record: '+p['id'])
        seen.add(p['id'])
    if not isinstance(data.get('papers'),list): raise ValueError('papers must be an array')
