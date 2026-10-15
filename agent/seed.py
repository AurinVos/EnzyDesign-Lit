"""Versioned, source-checked starting collection; not a systematic-review inclusion set.

Run `python -m agent.seed` only for a new empty dataset. The generator refuses
an existing dataset unless --reset is explicitly supplied. No network calls.
"""
from __future__ import annotations
import argparse
from .common import ROOT, SCHEMA, write_json, validate_dataset

D='Discovery'; E='Engineering'; G='Design'
X='Experimental screening'; B='Bioinformatics / genome mining'; DE='Directed evolution'
ML='Machine learning'; PLM='Protein language models'; S='Structure-based design'
MD='Molecular simulation'; GM='Generative models'; AL='Active learning'; AG='Agentic workflows'
ASSAY='Experimental assays reported'; COMP='Computational evaluation'; REV='Review / perspective'
N='Natural'; V='Engineered variants'; NEW='De novo / generated'; MIX='Mixed / general'

# Each entry has its own primary-source URL; summaries are original paraphrases.
ROWS = [
('10.1038/s43588-026-01049-y','2026-09-10','MutexaGPT: an intuition-to-design translator for physics-based enzyme engineering','Shao et al.','Nature Computational Science',[E,G],[AG,MD,S],['Hydrolases','Transferases'],V,ASSAY,
 'Translates qualitative engineering ideas into physics-based calculations and variant selection, with retrospective methyltransferase analysis and prospective amylase experiments.',
 'https://www.nature.com/articles/s43588-026-01049-y',
 'Includes retrospective and prospective cases; it is not a direct activity predictor. The record does not assert that every ranked variant was experimentally validated.'),
('10.1038/s41586-025-09747-9','2025-12-03','Computational enzyme design by catalytic motif scaffolding','Braun et al.','Nature',[G],[S,GM,ML],['Designed catalysts'],NEW,ASSAY,
 'Combines catalytic motif placement, diffusion and atomistic modelling in Riff-Diff, with experimental evaluation of retro-aldol and Morita–Baylis–Hillman catalysts.',
 'https://www.nature.com/articles/s41586-025-09747-9',
 'Activity and structural measurements are reported for selected designs; that does not validate all generated sequences.'),
('10.1038/s41586-025-09746-w','2025-12-03','Computational design of metallohydrolases','Kim et al.','Nature',[G],[S,GM],['Hydrolases','Designed catalysts'],NEW,ASSAY,
 'Uses generative scaffolding and active-site ensemble evaluation to construct zinc-dependent hydrolases, followed by experimental characterization of selected designs.',
 'https://www.nature.com/articles/s41586-025-09746-w',
 'The study reports experimental catalytic characterization. Substrate scope and assay conditions must be checked in the original study.'),
('10.1038/s41586-025-09136-2','2025-06-18','Complete computational design of high-efficiency Kemp elimination enzymes','Listov et al.','Nature',[G,E],[S,MD],['Designed catalysts'],NEW,ASSAY,
 'Constructs and computationally optimizes Kemp eliminases, testing whether designed active sites can achieve efficient catalysis without extensive experimental library screening.',
 'https://www.nature.com/articles/s41586-025-09136-2',
 'Experimental validation concerns the selected designs and their reported reaction, not arbitrary functions or scaffolds.'),
('10.1126/science.adu2454','2025','Computational design of serine hydrolases','Lauko et al.','Science',[G],[S,GM],['Hydrolases','Designed catalysts'],NEW,ASSAY,
 'Combines generative backbone construction and active-site ensemble assessment to design serine hydrolases and evaluate their catalytic activity experimentally.',
 'https://pubmed.ncbi.nlm.nih.gov/39946508/',
 'Experimental activity is reported. The journal publication and earlier preprint should be treated as versions of one study, not independent evidence.'),
('10.1038/s41467-025-55987-8','2025-01-16','Active learning-assisted directed evolution','Yang et al.','Nature Communications',[E],[AL,ML,DE],['Heme enzymes'],V,ASSAY,
 'Combines uncertainty-aware model selection with iterative experiments to navigate combinatorial enzyme variants during a directed-evolution campaign.',
 'https://www.nature.com/articles/s41467-025-55987-8',
 'Prospective experimental rounds are reported. Performance depends on the experimental landscape, acquisition strategy and available observations.'),
('10.1038/s44286-023-00002-4','2024-01-11','Self-driving laboratories to autonomously navigate the protein fitness landscape','Rapp, Bremer & Romero','Nature Chemical Engineering',[E],[AL,ML,X],['Hydrolases'],V,ASSAY,
 'Connects automated experiments with data-driven selection in a self-driving laboratory, using enzyme thermal tolerance as a protein-engineering objective.',
 'https://www.nature.com/articles/s44286-023-00002-4',
 'Robotic experiments are reported for glycoside hydrolases. Laboratory autonomy is not synonymous with a language-model agent.'),
('10.1126/science.adf2465','2023-03-31','Enzyme function prediction using contrastive learning','Yu et al.','Science',[D],[ML,B],['Multiple enzyme families'],N,ASSAY,
 'Introduces CLEAN for contrastive-learning-based enzyme function prediction, combining computational benchmarks with experimental demonstrations on selected enzymes.',
 'https://experts.illinois.edu/en/publications/enzyme-function-prediction-using-contrastive-learning/',
 'Selected functions are tested in vitro; the larger automatically annotated collection is not equivalent to experimentally characterized enzymes.'),
('10.1038/s41586-023-05696-3','2023-02-22','De novo design of luciferases using deep learning','Yeh et al.','Nature',[G],[GM,S,ML],['Oxidoreductases','Designed catalysts'],NEW,ASSAY,
 'Uses deep-learning-based scaffold generation and active-site design to produce luciferases, followed by biochemical testing of light-producing catalysis.',
 'https://www.nature.com/articles/s41586-023-05696-3',
 'Experimental luminescence and catalytic characterization support selected designs. Generalization beyond the tested substrate systems is not established here.'),
('10.1038/s41587-022-01618-2','2023-01-26','Large language models generate functional protein sequences across diverse families','Madani et al.','Nature Biotechnology',[D,G],[PLM,GM],['Hydrolases'],NEW,ASSAY,
 'Uses a conditional protein language model to generate sequences, with experimental lysozyme testing demonstrating catalytic function in a subset of generated proteins.',
 'https://www.nature.com/articles/s41587-022-01618-2',
 'Discovery denotes previously unknown sequence–function relationships in generated sequence space. Experimental support must not be extrapolated to all families or generated outputs.'),
('10.1002/jms.4951','2023-05-31','The use of proton transfer reaction mass spectrometry for high throughput screening of terpene synthases','Di Girolamo et al.','Journal of Mass Spectrometry',[E],[X],['Terpene synthases'],V,ASSAY,
 'Evaluates proton-transfer-reaction mass spectrometry as a rapid screening readout for terpene synthases and their engineered variants.',
 'https://analyticalsciencejournals.onlinelibrary.wiley.com/doi/10.1002/jms.4951',
 'A screening-method study; rapid signal detection does not by itself replace compound identification and calibrated quantification.'),
('10.1038/s41586-022-04599-z','2022-04-27','Machine learning-aided engineering of hydrolases for PET depolymerization','Lu et al.','Nature',[E],[ML,S,X],['Hydrolases'],V,ASSAY,
 'Uses structure-informed machine learning to propose PET hydrolase variants, then measures enzyme stability and plastic depolymerization performance.',
 'https://www.nature.com/articles/s41586-022-04599-z',
 'Assay and substrate conditions are essential for comparing plastic-depolymerization claims across studies.'),
('10.1038/s41592-021-01100-y','2021-04-07','Low-N protein engineering with data-efficient deep learning','Biswas et al.','Nature Methods',[E],[PLM,ML],['Hydrolases'],V,ASSAY,
 'Combines pretrained protein representations with small experimental datasets to guide sequence optimization, including an enzyme engineering demonstration.',
 'https://www.nature.com/articles/s41592-021-01100-y',
 'The paper includes enzyme and non-enzyme tasks. Inclusion here refers to the enzyme-relevant evidence rather than all protein benchmarks.'),
('10.1371/journal.pcbi.1008197','2021-03-22','Integrating structure-based machine learning and co-evolution to investigate specificity in plant sesquiterpene synthases','Durairaj et al.','PLOS Computational Biology',[D],[ML,B,S],['Terpene synthases'],N,ASSAY,
 'Combines structural features and co-evolution to investigate sesquiterpene synthase pathway specificity, with experimental characterization of selected predictions.',
 'https://pubmed.ncbi.nlm.nih.gov/33750949/',
 'Predictions concern defined early reaction-pathway groupings. They are not complete product-spectrum or kinetic predictions.'),
('10.1016/j.abb.2020.108647','2020','The santalene synthase from Cinnamomum camphora: Reconstruction of a sesquiterpene synthase from a monoterpene synthase','Di Girolamo et al.','Archives of Biochemistry and Biophysics',[D,E],[X,S],['Terpene synthases'],MIX,ASSAY,
 'Investigates related terpene synthases and reconstructed variants to connect sequence changes with monoterpene versus sesquiterpene catalytic behavior.',
 'https://www.sciencedirect.com/science/article/pii/S0003986120306561',
 'Both enzyme characterization and scaffold modification are relevant, so the record carries discovery and engineering objectives.'),
('10.1111/1462-2920.15257','2020-09-28','An ultrahigh-throughput screening platform based on flow cytometric droplet sorting for mining novel enzymes from metagenomic libraries','Ma et al.','Environmental Microbiology',[D],[X,B],['Hydrolases'],N,ASSAY,
 'Uses droplet compartments and flow-cytometric sorting to functionally screen metagenomic libraries and identify previously uncharacterized esterases.',
 'https://pubmed.ncbi.nlm.nih.gov/32985743/',
 'Functional screening complements sequence-based annotation. This record uses the first-online year rather than the later issue year.'),
('10.1038/s41586-020-2546-8','2020-07-22','Discovery and engineering of colchicine alkaloid biosynthesis','Nett, Lau & Sattely','Nature',[D],[B,X],['Cytochrome P450s','Transferases'],N,ASSAY,
 'Combines pathway-guided enzyme discovery and biochemical reconstruction to assign functions in plant alkaloid biosynthesis, including an unusual oxidative transformation.',
 'https://www.nature.com/articles/s41586-020-2546-8',
 'The title includes pathway engineering. It is not automatically tagged as enzyme engineering because pathway assembly need not modify enzyme sequences.'),
('10.1038/s41586-020-2149-4','2020','An engineered PET depolymerase to break down and recycle plastic bottles','Tournier et al.','Nature',[E],[S,X],['Hydrolases'],V,ASSAY,
 'Engineers a PET-degrading hydrolase and evaluates enzymatic depolymerization in a plastic-recycling context, linking enzyme properties to process performance.',
 'https://www.nature.com/articles/s41586-020-2149-4',
 'Enzyme performance and process outcomes are related but not interchangeable. This record does not claim a normalized ranking against other PETases.'),
('10.1038/s41592-019-0496-6','2019-07-15','Machine-learning-guided directed evolution for protein engineering','Yang, Wu & Arnold','Nature Methods',[E],[ML,DE,AL],['Multiple enzyme families'],MIX,REV,
 'Reviews how machine learning can guide directed evolution, emphasizing sequence–function modelling and the choice of variants for experimental evaluation.',
 'https://www.nature.com/articles/s41592-019-0496-6',
 'This is a review, not an independent experimental campaign. It is displayed separately from primary studies.'),
('10.1038/ncomms10008','2015-12-07','Ultrahigh-throughput discovery of promiscuous enzymes by picodroplet functional metagenomics','Colin et al.','Nature Communications',[D],[X,B],['Hydrolases'],N,ASSAY,
 'Screens metagenomic libraries in microfluidic droplets to discover catalytic activities that are difficult to infer from sequence similarity alone.',
 'https://pubmed.ncbi.nlm.nih.gov/26639611/',
 'Experimentally identified promiscuous activities need not be the physiological functions of the source enzymes.'),
('10.1016/j.bbapap.2015.04.015','2015-04-18','Enzyme Function Initiative-Enzyme Similarity Tool (EFI-EST): A web tool for generating protein sequence similarity networks','Gerlt et al.','Biochimica et Biophysica Acta',[D],[B],['Multiple enzyme families'],N,COMP,
 'Provides sequence-similarity-network generation to organize enzyme families and support the prioritization of proteins for functional characterization.',
 'https://pubmed.ncbi.nlm.nih.gov/25900361/',
 'Network similarity is a computational guide; it is not direct evidence that every clustered sequence catalyzes the same reaction.'),
('10.1073/pnas.1215251110','2012-12-31','Navigating the protein fitness landscape with Gaussian processes','Romero, Krause & Arnold','PNAS',[E],[ML,AL,S],['Cytochrome P450s'],V,ASSAY,
 'Uses Gaussian-process models to guide exploration of protein fitness landscapes and experimentally evaluate selected cytochrome P450 chimeras.',
 'https://pubmed.ncbi.nlm.nih.gov/23277561/',
 'First published online in 2012 and assigned to a 2013 issue. The timeline uses the online date to avoid shifting the historical sequence.'),
('10.1126/science.1188934','2010-06-17','Biocatalytic asymmetric synthesis of chiral amines from ketones applied to sitagliptin manufacture','Savile et al.','Science',[E,G],[DE,S,X],['Transferases'],V,ASSAY,
 'Combines enzyme redesign and directed evolution to develop a transaminase suited to an industrial asymmetric synthesis application.',
 'https://pubmed.ncbi.nlm.nih.gov/20558668/',
 'Manufacturing suitability is application-specific and depends on the original study’s substrate, selectivity and process constraints.'),
('10.1038/nature06879','2008-03-19','Kemp elimination catalysts by computational enzyme design','Röthlisberger et al.','Nature',[G,E],[S,DE],['Designed catalysts'],V,ASSAY,
 'Places designed catalytic sites into protein scaffolds, experimentally tests Kemp elimination, and improves selected catalysts through directed evolution.',
 'https://www.nature.com/articles/nature06879',
 'A designed active site in an existing scaffold is distinguished from generation of an entirely new protein backbone.'),
('10.1126/science.1152692','2008-03-07','De novo computational design of retro-aldol enzymes','Jiang et al.','Science',[G],[S,MD],['Designed catalysts'],V,ASSAY,
 'Constructs alternative catalytic motifs in protein scaffolds and tests retro-aldol activity, using structural characterization to examine design accuracy.',
 'https://pubmed.ncbi.nlm.nih.gov/18323453/',
 'The novelty is in designed catalysis within scaffold proteins; this is not automatically classified as a fully generated backbone.'),
('10.1073/pnas.90.12.5618','1993-06-15','Tuning the activity of an enzyme for unusual environments: sequential random mutagenesis of subtilisin E for catalysis in dimethylformamide','K. Chen & F. H. Arnold','PNAS',[E],[DE,X],['Hydrolases'],V,ASSAY,
 'Uses sequential mutagenesis and screening to adapt subtilisin activity to an unusual solvent environment, providing an early directed-evolution example.',
 'https://pubmed.ncbi.nlm.nih.gov/8516309/',
 'Activity is measured under the study’s solvent and assay conditions; this does not establish universal improvement of the enzyme.'),
]

def build_seed():
    records=[]
    for doi,pub,title,cite,journal,obj,methods,families,space,val,summary,url,evidence in ROWS:
        records.append(dict(id='doi:'+doi,doi=doi,title=title,citation=cite,authors=[],authors_complete=False,
            year=int(pub[:4]),published_date=pub,date_precision={4:'year',7:'month',10:'day'}[len(pub)],
            journal=journal,objectives=obj,methods=methods,enzyme_families=families,sequence_space=space,
            validation=val,status='curated',record_type='Review' if val==REV else 'Research article',
            abstract='',summary=summary,evidence_note=evidence,source_url=url,first_seen='2026-10-15',checked_on='2026-10-15',
            date_note='Year precision retained where an exact first-online date was not independently resolved.' if len(pub)==4 else 'First-online or source-indexed publication date; see provenance.',
            provenance=[dict(source='Publisher or primary bibliographic record',url=url,accessed_on='2026-10-15',basis='title_abstract',checked_fields=['title','doi','publication metadata','abstract-level scope'])],
            classification=dict(method='AI-assisted source-checked starter selection',basis='title_abstract',note='Not an independent expert review or full-text systematic inclusion.'),
            resource_links=[],related_ids=[],targets=[],annotations={}))
    bydoi={p['doi']:p for p in records}
    for doi,yr in [('10.1038/s41586-025-09747-9',2026),('10.1038/s41586-025-09746-w',2026),('10.1111/1462-2920.15257',2021),('10.1073/pnas.1215251110',2013)]: bydoi[doi]['issue_year']=yr
    bydoi['10.1126/science.adu2454']['related_ids']=['doi:10.1101/2024.08.29.610411']
    bydoi['10.1038/s41586-025-09746-w']['resource_links']=[{'label':'RFdiffusion2','kind':'Code','url':'https://github.com/RosettaCommons/RFdiffusion2'},{'label':'PLACER','kind':'Code','url':'https://github.com/baker-laboratory/PLACER'}]
    bydoi['10.1038/s43588-026-01049-y']['resource_links']=[{'label':'EnzyHTP-GPT','kind':'Code','url':'https://github.com/ChemBioHTP/EnzyHTP-GPT/'}]
    return {'schema_version':SCHEMA,'meta':{'title':'Enzyme Evidence Atlas','release':'0.1.0','seed_checked_on':'2026-10-15','seed_type':'Selected, AI-assisted source-checked literature collection',
            'scope':'Enzyme discovery, engineering and design, including experimental and computational approaches. Not restricted to AI.',
            'coverage_note':'An illustrative starting collection, not an exhaustive or systematic review. Curated labels are source-checked AI-assisted annotations, not independent expert decisions.',
            'last_search':None,'upstream_author':'Bas van der Velden','upstream_repository':'https://github.com/basvandervelden/ai_food_safety_review'},
            'papers':sorted(records,key=lambda p:(p['published_date'],p['id']),reverse=True)}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reset',action='store_true');args=parser.parse_args()
    path=ROOT/'data/papers.json'
    if path.exists() and not args.reset: parser.error('Dataset exists. --reset deliberately replaces all records and review decisions.')
    data=build_seed();validate_dataset(data);write_json(path,data)
    print(f'Wrote {len(data["papers"])} source-linked seed records.')

if __name__=='__main__': main()
