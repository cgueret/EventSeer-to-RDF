'''
Created on 30 Jun 2011

@author: cgueret
'''
import urllib2
from BeautifulSoup import BeautifulSoup
from objects import SWC, CFP, ICAL, FOAF, DCT, LODE, LDES, NAMED_GRAPHS_BASE, SIOCT
from rdflib import ConjunctiveGraph, Literal, RDF, RDFS, URIRef
from datetime import datetime

class Topic(object):
    def __init__(self, entity_id):
        '''
        Constructor 
        @param entity_id: an topic id such as 't/data_analysis'
        '''
        # Keep track of the ID
        self.entity_id = entity_id

        # Containers for the data 
        self.rdf_data = None
        
    def load_data(self):
        # Get the document, process the data
        document = BeautifulSoup(urllib2.urlopen("http://eventseer.net/" + self.entity_id).read())
        self._process_data(document)
        del document
        
    def get_named_graph(self):
        '''
        Return the named graph for storing the data
        '''
        return URIRef(NAMED_GRAPHS_BASE + self.get_resource_name() + '.rdf')
    
    def get_resource_name(self):
        '''
        Return the named graph for storing the data
        '''
        return 'topic_' + self.entity_id[2:]
    
    def get_rdf_data(self):
        '''
        Return the content of the RDF graph
        '''
        return self.rdf_data

    def _process_data(self, document):
        '''
        Creates the RDF graph describing the topic
        @param document: the DOM document of the topic
        '''
        # Create the graph
        graph = ConjunctiveGraph()
        graph.bind('swc', SWC)
        graph.bind('cfp', CFP)
        graph.bind('ical', ICAL)
        graph.bind('foaf', FOAF)
        graph.bind('dct', DCT)
        graph.bind('lode', LODE)
        
        # Init the event
        topic_event = LDES[self.get_resource_name()]
        graph.add((topic_event, RDF.type, SIOCT['Tag']))
        
        # Get the label
        label = document.find(id='inner_left').find('h1').text
        graph.add((topic_event, RDFS.label, Literal(label)))
        
        # Set the last modification date
        graph.add((self.get_named_graph(), DCT['modified'], Literal(datetime.now()))) 
        
        # Save the data
        self.rdf_data = graph.serialize()
