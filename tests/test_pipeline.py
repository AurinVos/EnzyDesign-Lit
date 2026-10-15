"""Deterministic, network-free unit/integration tests for the evidence pipeline."""
from __future__ import annotations
import copy
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from . import fixtures_helper as fx
from agent import common as c
from agent.classify import tag_candidate
from agent.providers import normalize_epmc,normalize_openalex,fetch_query,build_epmc_query,http_json,RetrievalError
from agent.update import merge_records,apply_decisions,year_windows,main
from agent.seed import build_seed
from agent.llm import suggest
from agent.render_static import render

class IdentityAndSafety(unittest.TestCase):
    def test_normalize_doi(self):self.assertEqual(c.normalize_doi('HTTPS://DOI.ORG/10.1234/ABC'),'10.1234/abc')
    def test_doi_prefix(self):self.assertEqual(c.normalize_doi('doi: 10.1234/AbC'),'10.1234/abc')
    def test_no_doi_stable_id(self):self.assertEqual(c.canonical_id(source='Europe PMC MED',source_id='123'),'europepmcmed:123')
    def test_no_invented_title_hash(self):
        with self.assertRaises(ValueError):c.canonical_id()
    def test_abstract_positions(self):self.assertEqual(c.abstract_from_index({'enzymes':[2],'Find':[0],'new':[1]}),'Find new enzymes')
    def test_html_removed(self):self.assertEqual(c.strip_html('<b>A</b> &amp; B'),'A & B')
    def test_script_escape(self):self.assertNotIn('</script>',c.script_json({'title':'</script><script>bad</script>'}))
    def test_csv_formula(self):
        for text in ['=1+1','  +SUM(A1)','@evil','-2','\t=1']:
            with self.subTest(text=text):self.assertTrue(c.csv_cell(text).startswith("'"))
    def test_csv_plain(self):self.assertEqual(c.csv_cell(['one','two']),'one; two')
    def test_bad_url(self):
        for url in ['javascript:alert(1)','data:text/html,evil','https://user:pass@example.org/','//example.org']:
            with self.subTest(url=url),self.assertRaises(ValueError):c.safe_url(url)
    def test_config_hash_stable(self):self.assertEqual(c.fingerprint({'a':1,'b':2}),c.fingerprint({'b':2,'a':1}))

class Records(unittest.TestCase):
    def setUp(self):self.seed=build_seed();self.p=copy.deepcopy(self.seed['papers'][0])
    def test_seed_valid(self):c.validate_dataset(self.seed)
    def test_unique_dois(self):self.assertEqual(len(self.seed['papers']),len({p['doi'] for p in self.seed['papers']}))
    def test_no_false_expert_seed(self):self.assertTrue(all(p['status']=='curated' and not p.get('review') for p in self.seed['papers']))
    def test_all_seed_sources(self):self.assertTrue(all(p['provenance'] and p['source_url'] for p in self.seed['papers']))
    def test_year_precision(self):self.p.update(published_date='2025',year=2025,date_precision='year');c.validate_record(self.p)
    def test_month_precision(self):self.p.update(published_date='2025-03',year=2025,date_precision='month');c.validate_record(self.p)
    def test_invalid_day(self):
        self.p.update(published_date='2025-02-30',year=2025,date_precision='day')
        with self.assertRaises(ValueError):c.validate_record(self.p)
    def test_precision_mismatch(self):
        self.p['date_precision']='year'
        with self.assertRaises(ValueError):c.validate_record(self.p)
    def test_illegal_objective(self):
        self.p['objectives']=['Everything']
        with self.assertRaises(ValueError):c.validate_record(self.p)
    def test_duplicate_objective(self):
        self.p['objectives']=['Discovery','Discovery']
        with self.assertRaises(ValueError):c.validate_record(self.p)
    def test_duplicate_paper(self):
        self.seed['papers'].append(self.seed['papers'][0])
        with self.assertRaises(ValueError):c.validate_dataset(self.seed)
    def test_verified_needs_reviewer(self):
        self.p['status']='verified'
        with self.assertRaises(ValueError):c.validate_record(self.p)
    def test_online_issue_distinction(self):
        p=next(x for x in self.seed['papers'] if x['doi']=='10.1073/pnas.1215251110');self.assertEqual((p['year'],p['issue_year']),(2012,2013))
    def test_non_natural_discovery(self):self.assertTrue(any('Discovery' in p['objectives'] and p['sequence_space']=='De novo / generated' for p in self.seed['papers']))
    def test_no_pathway_engineering_conflation(self):
        p=next(x for x in self.seed['papers'] if x['doi']=='10.1038/s41586-020-2546-8');self.assertNotIn('Engineering',p['objectives'])

class Providers(unittest.TestCase):
    def test_epmc_doi(self):self.assertEqual(normalize_epmc(fx.EPMC,'2026-10-15')['id'],'doi:10.1234/fixture')
    def test_epmc_no_doi(self):
        row={**fx.EPMC,'doi':''};self.assertEqual(normalize_epmc(row,'2026-10-15')['id'],'europepmcmed:12345')
    def test_epmc_preprint(self):self.assertEqual(normalize_epmc({**fx.EPMC,'source':'PPR'},'2026-10-15')['record_type'],'Preprint')
    def test_epmc_review(self):self.assertEqual(normalize_epmc({**fx.EPMC,'pubTypeList':{'pubType':['Review']}},'2026-10-15')['record_type'],'Review')
    def test_openalex_missing_journal(self):self.assertEqual(normalize_openalex(fx.OPENALEX,'2026-10-15')['journal'],'Source not specified')
    def test_openalex_missing_doi(self):self.assertEqual(normalize_openalex({**fx.OPENALEX,'doi':None},'2026-10-15')['id'],'openalex:W12345')
    def test_future_year(self):
        with self.assertRaises(ValueError):normalize_epmc({**fx.EPMC,'firstPublicationDate':'2027'},'2026-10-15')
    def test_future_month(self):
        with self.assertRaises(ValueError):normalize_epmc({**fx.EPMC,'firstPublicationDate':'2026-12'},'2026-10-15')
    def test_bad_calendar_date(self):
        with self.assertRaises(ValueError):normalize_epmc({**fx.EPMC,'firstPublicationDate':'2026-02-31'},'2026-10-15')
    def test_no_missing_dates(self):
        with self.assertRaises(ValueError):normalize_epmc({**fx.EPMC,'firstPublicationDate':'','pubYear':''},'2026-10-15')
    def test_incremental_includes_indexing(self):self.assertIn('FIRST_IDATE',build_epmc_query('enzyme','2026-01-01','2026-10-15'))
    def test_historical_publication_date(self):self.assertNotIn('FIRST_IDATE',build_epmc_query('enzyme','2020-01-01','2020-12-31','historical'))
    def test_pagination_truncation(self):
        client=lambda *_a,**_k:{'hitCount':200,'nextCursorMark':'abc','resultList':{'result':[fx.EPMC]}}
        rows,r=fetch_query('europepmc',fx.QUERY,'2026-01-01','2026-10-15',max_pages=1,client=client)
        self.assertTrue(r['truncated']);self.assertEqual(len(rows),1)
    def test_pagination_complete(self):
        pages=iter([{'hitCount':2,'nextCursorMark':'abc','resultList':{'result':[fx.EPMC]}},{'hitCount':2,'nextCursorMark':'def','resultList':{'result':[{**fx.EPMC,'id':'12346','doi':'10.1234/other'}]}}])
        with patch('agent.providers.time.sleep'):
            rows,r=fetch_query('europepmc',fx.QUERY,'2026-01-01','2026-10-15',max_pages=2,client=lambda *_a,**_k:next(pages))
        self.assertFalse(r['truncated']);self.assertEqual(r['retrieved'],2)
    def test_invalid_record_not_silent(self):
        client=lambda *_a,**_k:{'hitCount':1,'resultList':{'result':[{**fx.EPMC,'id':''}]}}
        rows,r=fetch_query('europepmc',fx.QUERY,'2026-01-01','2026-10-15',client=client)
        self.assertEqual(len(r['invalid_records']),1)
    def test_api_error_not_empty_success(self):
        with self.assertRaises(RetrievalError):fetch_query('europepmc',fx.QUERY,'2026-01-01','2026-10-15',client=lambda *_a,**_k:{'error':'bad query'})
    def test_openalex_key_required(self):
        with patch.dict('os.environ',{},clear=True),self.assertRaises(RetrievalError):fetch_query('openalex',fx.QUERY,'2026-01-01','2026-10-15')
    def test_source_seen_date_is_retrieval(self):
        client=lambda *_a,**_k:{'hitCount':1,'resultList':{'result':[{**fx.EPMC,'firstPublicationDate':'2015-01-01'}]}}
        rows,r=fetch_query('europepmc',fx.QUERY,'2015-01-01','2015-12-31',client=client)
        from datetime import date
        self.assertEqual(rows[0]['first_seen'],date.today().isoformat())
    def test_retry_429(self):
        response=io.BytesIO(b'{"ok": true}');response.headers={}
        error=HTTPError('https://example.org',429,'slow',{'Retry-After':'0'},None)
        with patch('agent.providers.urlopen',side_effect=[error,response]) as mock,patch('agent.providers.time.sleep'):
            self.assertEqual(http_json('https://example.org'),{'ok':True});self.assertEqual(mock.call_count,2)
    def test_no_retry_403(self):
        error=HTTPError('https://example.org',403,'forbidden',{},None)
        with patch('agent.providers.urlopen',side_effect=error) as mock,self.assertRaises(RetrievalError):http_json('https://example.org')
        self.assertEqual(mock.call_count,1)

class Curation(unittest.TestCase):
    def test_no_heuristic_exclusions(self):
        p=tag_candidate('A surprising molecular mechanism','No enzyme keyword here.')
        self.assertEqual(p['status'],'candidate');self.assertEqual(p['validation'],'Not assessed')
    def test_no_automatic_assay_inference(self):self.assertEqual(tag_candidate('Experimental enzyme discovery')['validation'],'Not assessed')
    def test_merge_keeps_curated_labels(self):
        p=build_seed()['papers'][0];incoming={**p,'summary':'unreviewed replacement','status':'candidate'}
        self.assertEqual(merge_records([p],[incoming])[0]['summary'],p['summary'])
    def test_merge_keeps_exclusion(self):
        p=build_seed()['papers'][0];p['status']='excluded';self.assertEqual(merge_records([p],[p])[0]['status'],'excluded')
    def test_merge_new_is_candidate(self):
        p=build_seed()['papers'][0];self.assertEqual(merge_records([],[p])[0]['status'],'candidate')
    def test_merge_doi_dedup(self):
        p=build_seed()['papers'][0];self.assertEqual(len(merge_records([],[p,p,p])),1)
    def test_merge_does_not_mutate(self):
        p=build_seed()['papers'][0];saved=copy.deepcopy(p);merge_records([p],[p]);self.assertEqual(p,saved)
    def test_valid_decision(self):
        p=build_seed()['papers'][0];d=fx.decision(p['id']);out=apply_decisions([p],{'schema_version':c.SCHEMA,'decisions':[d]});self.assertEqual(out[0]['status'],'verified');self.assertEqual(len(out[0]['review_history']),1);c.validate_record(out[0])
    def test_empty_reviewer(self):
        p=build_seed()['papers'][0];d=fx.decision(p['id']);d['reviewer']=' '
        with self.assertRaises(ValueError):apply_decisions([p],{'schema_version':c.SCHEMA,'decisions':[d]})
    def test_missing_reason(self):
        p=build_seed()['papers'][0];d=fx.decision(p['id']);d['reason']=''
        with self.assertRaises(ValueError):apply_decisions([p],{'schema_version':c.SCHEMA,'decisions':[d]})
    def test_unknown_review_id(self):
        with self.assertRaises(ValueError):apply_decisions([] ,{'schema_version':c.SCHEMA,'decisions':[fx.decision('doi:unknown')]})
    def test_unsupported_review_basis(self):
        p=build_seed()['papers'][0];d=fx.decision(p['id']);d['basis']='imagined'
        with self.assertRaises(ValueError):apply_decisions([p],{'schema_version':c.SCHEMA,'decisions':[d]})
    def test_year_window_no_gaps(self):self.assertEqual(list(year_windows('2024-11-01','2026-03-02')),[('2024-11-01','2024-12-31'),('2025-01-01','2025-12-31'),('2026-01-01','2026-03-02')])

class OptionalLLM(unittest.TestCase):
    def test_explicit_model_and_key(self):
        with patch.dict('os.environ',{},clear=True),self.assertRaises(ValueError):suggest(fx.candidate())
    def test_status_never_upgraded(self):
        p=fx.candidate()
        client=lambda *_a,**_k:{'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'objectives':['Discovery'],'methods':['Machine learning'],'summary':'Candidate summary.','rationale':'Title supports a prediction task.'})}}]}
        with patch.dict('os.environ',{'OPENAI_API_KEY':'test','OPENAI_MODEL':'test-model'}):suggest(p,client)
        self.assertEqual(p['status'],'candidate');self.assertEqual(p['validation'],'Not assessed')
    def test_model_cannot_add_expert_status(self):
        p=fx.candidate();client=lambda *_a,**_k:{'choices':[{'finish_reason':'stop','message':{'content':'{"objectives":["Invented"],"methods":[],"summary":"x","rationale":"y"}'}}]}
        with patch.dict('os.environ',{'OPENAI_API_KEY':'test','OPENAI_MODEL':'test-model'}),self.assertRaises(ValueError):suggest(p,client)

class BuildAndCLI(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        for folder in ('assets','config'):shutil.copytree(c.ROOT/folder,self.root/folder)
        c.write_json(self.root/'data/papers.json',build_seed())
        self.input=self.root/'input.json';c.write_json(self.input,[fx.candidate()])
    def tearDown(self):self.tmp.cleanup()
    def test_offline_import(self):
        before=len(build_seed()['papers']);self.assertEqual(main(['--root',str(self.root),'--input',str(self.input),'--as-of','2026-10-15']),0)
        data=c.read_json(self.root/'data/papers.json');self.assertEqual(len(data['papers']),before+1);self.assertIsNone(data['meta']['last_search'])
    def test_dry_run_no_write(self):
        path=self.root/'data/papers.json';old=path.read_bytes();main(['--root',str(self.root),'--input',str(self.input),'--dry-run']);self.assertEqual(path.read_bytes(),old)
    def test_failed_network_preserves_dataset(self):
        path=self.root/'data/papers.json';old=path.read_bytes()
        with patch('agent.update.fetch_query',side_effect=RetrievalError('offline')):self.assertEqual(main(['--root',str(self.root)]),1)
        self.assertEqual(path.read_bytes(),old)
    def test_unknown_query_is_error(self):self.assertEqual(main(['--root',str(self.root),'--query-id','not-configured']),1)
    def test_strict_truncation_preserves_data(self):
        path=self.root/'data/papers.json';old=path.read_bytes();report={'retrieved':1,'reported_matches':100,'truncated':True,'provider':'europepmc','query_id':'discovery'}
        with patch('agent.update.fetch_query',return_value=([fx.candidate()],report)):
            self.assertEqual(main(['--root',str(self.root),'--query-id','discovery','--require-complete']),1)
        self.assertEqual(path.read_bytes(),old)
    def test_build_includes_attribution(self):
        render(self.root);html=(self.root/'Enzyme_Evidence_Atlas.html').read_text();self.assertIn('Bas van der Velden',html);self.assertIn('window.ENZYME_ATLAS',html);self.assertNotIn('<!-- CARDS -->',html)
    def test_standalone_no_remote_script(self):
        render(self.root);html=(self.root/'Enzyme_Evidence_Atlas.html').read_text();self.assertNotIn('<script src=',html);self.assertNotIn('<link rel="stylesheet"',html)
    def test_build_has_no_candidate_in_static_selected(self):
        data=c.read_json(self.root/'data/papers.json');data['papers'].append(fx.candidate());c.write_json(self.root/'data/papers.json',data);render(self.root)
        html=(self.root/'index.html').read_text();self.assertNotIn('Fixture enzyme discovery candidate',html)
    def test_html_escape(self):
        data=c.read_json(self.root/'data/papers.json');data['papers'][0]['title']='</script><img src=x onerror=alert(1)>';c.write_json(self.root/'data/papers.json',data);render(self.root)
        html=(self.root/'Enzyme_Evidence_Atlas.html').read_text();self.assertNotIn('<img src=x',html);self.assertIn('&lt;img',html)
    def test_no_fake_live_run_in_seed(self):self.assertIsNone(build_seed()['meta']['last_search'])


class RegressionChecks(unittest.TestCase):
    def test_collection_options_well_formed(self):
        text=(c.ROOT/'assets/template.html').read_text();self.assertNotIn('</option value',text)
        from html.parser import HTMLParser
        class Options(HTMLParser):
            in_collection=False;values=[]
            def handle_starttag(self,tag,attrs):
                attrs=dict(attrs)
                if tag=='select' and attrs.get('id')=='filter-status':self.in_collection=True
                if tag=='option' and self.in_collection:self.values.append(attrs.get('value'))
            def handle_endtag(self,tag):
                if tag=='select':self.in_collection=False
        parser=Options();parser.feed(text)
        self.assertEqual(parser.values,['selected','all','candidate','verified','excluded'])
    def test_null_journal_accepted(self):self.assertEqual(normalize_epmc({**fx.EPMC,'journalInfo':None},'2026-10-15')['journal'],'Source not specified')
    def test_malformed_doi_is_reported(self):
        client=lambda *_a,**_k:{'hitCount':1,'resultList':{'result':[{**fx.EPMC,'doi':'not-a-doi'}]}}
        rows,report=fetch_query('europepmc',fx.QUERY,'2026-01-01','2026-10-15',client=client)
        self.assertEqual(rows,[]);self.assertEqual(len(report['invalid_records']),1)
    def test_nonobject_source_is_reported(self):
        client=lambda *_a,**_k:{'hitCount':1,'resultList':{'result':[None]}}
        rows,report=fetch_query('europepmc',fx.QUERY,'2026-01-01','2026-10-15',client=client)
        self.assertEqual(rows,[]);self.assertEqual(len(report['invalid_records']),1)
    def test_publish_copy_preserves_git_directory(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('publisher',c.ROOT/'scripts/fork_and_publish.py');publisher=importlib.util.module_from_spec(spec);spec.loader.exec_module(publisher)
        with tempfile.TemporaryDirectory() as td:
            target=Path(td);(target/'.git').mkdir();(target/'.git/keep').write_text('history')
            publisher.copy_release(target);self.assertEqual((target/'.git/keep').read_text(),'history');self.assertTrue((target/'LICENSE').exists())

if __name__=='__main__':unittest.main()
