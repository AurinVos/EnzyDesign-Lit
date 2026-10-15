"""Synthetic fixture data, never shipped as real publication evidence."""
from agent.providers import normalize_epmc
from agent.classify import tag_candidate
EPMC={'id':'12345','source':'MED','doi':'10.1234/FIXTURE','title':'Fixture enzyme discovery candidate','authorString':'Fixture Author','firstPublicationDate':'2026-01-02','pubYear':'2026','abstractText':'A synthetic test record for machine learning enzyme discovery.','journalInfo':{'journal':{'title':'Test fixture, not a journal'}}}
OPENALEX={'id':'https://openalex.org/W12345','doi':'https://doi.org/10.1234/fixture','title':'Fixture enzyme discovery candidate','publication_date':'2026-01-02','publication_year':2026,'authorships':[],'primary_location':{'source':None},'abstract_inverted_index':{'Fixture':[0],'abstract':[1]}}
QUERY={'id':'discovery','europepmc':'TITLE_ABS:"enzyme discovery"','openalex':'enzyme discovery'}
def candidate():
    p=normalize_epmc(EPMC,'2026-10-15');p.update(tag_candidate(p['title'],p['abstract']));return p

def decision(rid):return {'id':rid,'status':'verified','reviewer':'TEST FIXTURE REVIEWER','reason':'Synthetic test decision, not a scientific review.','basis':'title_abstract','reviewed_on':'2026-10-15T12:00:00+00:00'}
