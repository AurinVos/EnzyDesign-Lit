"""Transparent candidate tagging, never automatic scientific inclusion."""
from __future__ import annotations
import re
from .common import CONFIG
VERSION='rules-1.0.0'
RULES={
 'objectives': {
  'Discovery': r'discover|genome mining|metagenom|function prediction|annotation|characteri[sz]',
  'Engineering': r'engineer|directed evolution|mutagen|mutant|mutation|variant|redesign',
  'Design': r'design|generati|de novo|scaffold|inverse fold|motif graft|hallucinat'},
 'methods': {
  'Experimental screening': r'screening|high.throughput|activity assay|enzyme assay',
  'Bioinformatics / genome mining': r'genome mining|metagenom|transcriptom|co.expression|sequence similarity|annotation',
  'Directed evolution': r'directed evolution|saturation mutagen|random mutagen',
  'Machine learning': r'machine learning|deep learning|neural network|random forest|contrastive learning',
  'Protein language models': r'protein language|language model|\bESM[- ]?\d|\bProGen\b',
  'Structure-based design': r'structure.based|structural design|catalytic motif|active.site design|computational design',
  'Molecular simulation': r'molecular dynamics|molecular simulation|quantum mechanics|QM/MM|molecular model',
  'Generative models': r'diffusion|generative|hallucination|\bProGen\b|flow matching',
  'Active learning': r'active learning|Bayesian optimization|self.driving|autonomous laborator',
  'Agentic workflows': r'multi.agent|LLM agent|agentic|MutexaGPT'},
 'enzyme_families': {
  'Terpene synthases':r'terpene synthase|terpene cyclase|sesquiterpene synthase',
  'Cytochrome P450s':r'cytochrome p450|\bCYP\d|\bP450\b',
  'Acyltransferases':r'acyltransferase|\bBAHD\b',
  'Glycosyltransferases':r'glycosyltransferase',
  'Hydrolases':r'hydrolase|PETase|depolymerase|cutinase|amylase|lipase|lysozyme',
  'Oxidoreductases':r'oxidoreductase|dehydrogenase|monooxygenase|oxidase|luciferase',
  'Transferases':r'transferase|transaminase',
  'Designed catalysts':r'Kemp elimin|de novo enzyme|retro.aldol|Diels.Alder'} }

def tag_candidate(title: str, abstract: str='') -> dict:
    text=title+' '+abstract
    result={key:[label for label,pat in mapping.items() if re.search(pat,text,re.I)] for key,mapping in RULES.items()}
    result.update(sequence_space='Not assessed', validation='Not assessed', status='candidate',
                  classification={'method':VERSION,'basis':'title_abstract','note':'Keyword suggestions only. No relevance exclusion and no assay validation inferred.'})
    return result
