'''
Created on 30 Jun 2011

@author: cgueret
'''
import urllib2
from BeautifulSoup import BeautifulSoup
from objects import SWC, CFP, ICAL, FOAF, DCT, LODE, LDES, NAMED_GRAPHS_BASE
from rdflib import ConjunctiveGraph, Literal, RDF, URIRef
from datetime import datetime
from objects.topics import Topic

class Person(object):
    def __init__(self, entity_id):
        '''
        Constructor 
        @param entity_id: an person id such as 'p/pieter_de_leenheer'
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
        Return the resource name
        '''
        return 'person_' + self.entity_id[2:]
    
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
        person_resource = LDES[self.get_resource_name()]
        graph.add((person_resource, RDF.type, FOAF['Person']))
        
        # Get the name
        name = document.find(id='inner_left').find('h1').text
        graph.add((person_resource, FOAF['name'], Literal(name)))

        # Get the center of interests and known persons
        for link in document.find(id='inner_left').find('p').findAll('a'):
            link = link.get('href')
            if link != None and link[:3] == '/t/':
                graph.add((person_resource, FOAF['topic_interest'], LDES[Topic(link[1:-1]).get_resource_name()]))
            if link != None and link[:3] == '/p/' and link[1:-1] != self.entity_id:
                graph.add((person_resource, FOAF['knows'], LDES[Person(link[1:-1]).get_resource_name()]))
                
        # Set the last modification date
        graph.add((self.get_named_graph(), DCT['modified'], Literal(datetime.now()))) 
        
        # Save the data
        self.rdf_data = graph.serialize()
