from rdflib import Namespace

BASE = 'http://linkeddata.few.vu.nl/eventseer/'
LDES = Namespace(BASE + "resource/")
NAMED_GRAPHS_BASE = Namespace(BASE + "data/")
SWRC = Namespace("http://swrc.ontoware.org/ontology#")
SWC = Namespace("http://data.semanticweb.org/ns/swc/ontology#")
CFP = Namespace("http://sw.deri.org/2005/08/conf/cfp.owl#")
ICAL = Namespace("http://www.w3.org/2002/12/cal/ical#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
DCT = Namespace("http://purl.org/dc/terms/")
LODE = Namespace("http://linkedevents.org/ontology/")
SIOCT = Namespace("http://rdfs.org/sioc/types#")

__all__ = [BASE, LDES, NAMED_GRAPHS_BASE, SWRC, SWC, CFP, ICAL, FOAF, DCT, LODE]
