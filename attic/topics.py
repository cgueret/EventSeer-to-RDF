'''
Created on Mar 24, 2011

@author: cgueret
'''
import urllib2
from BeautifulSoup import BeautifulSoup
from rdflib import ConjunctiveGraph, Literal, RDF, URIRef
from datetime import datetime
from objects import SWC, CFP, ICAL, FOAF, DCT, LODE, LDES, NAMED_GRAPHS_BASE, SIOCT

class Topic(object):
    def __init__(self, entity_name, entity_id):
        '''
        Constructor
        '''
        # Get the event page and compute its id
        self.entity_id = entity_id
        self.resource = LDES[self.entity_id]
        
        # Create the graph
        self.graph = ConjunctiveGraph()
        self.graph.bind('swc', SWC)
        self.graph.bind('cfp', CFP)
        self.graph.bind('ical', ICAL)
        self.graph.bind('foaf', FOAF)
        self.graph.bind('dct', DCT)
        self.graph.bind('lode', LODE)
        
        # Declare the type of the resource
        self.graph.add((self.resource, RDF.type, SIOCT['Tag']))
        self.graph.add((self.named_graph(), DCT['modified'], Literal(datetime.now()))) 
        
    def get_rdf_data(self):
        return self.graph.serialize()
    
    def named_graph(self):
        return URIRef(NAMED_GRAPHS_BASE + self.entity_id + '.rdf')
    
    def process(self, record, entity_url):
        # Get the document
        document = BeautifulSoup(urllib2.urlopen("http://eventseer.net" + entity_url).read())
        del document