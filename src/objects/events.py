'''
Created on Mar 24, 2011

@author: cgueret
'''
import json
import urllib2
import re
from BeautifulSoup import BeautifulSoup
from rdflib import ConjunctiveGraph, Literal, RDF, RDFS, URIRef
from datetime import datetime
from objects import SWC, CFP, ICAL, FOAF, DCT, LODE, LDES, BASE, NAMED_GRAPHS_BASE
from util.linking import get_location
from objects.topics import Topic
from objects.persons import Person


class Event(object):
    def __init__(self, entity_id):
        '''
        Constructor 
        @param entity_id: an event id such as 'e/16589'
        '''
        # Keep track of the ID
        self.entity_id = entity_id
        if re.match(r"^e/[0-9]+$", entity_id) == None:
            raise Exception('Invalid event identifier %s' % entity_id)

        # Containers for the data 
        self.cfp_data = ""
        self.rdf_data = None
        
        # Set of cited persons and topics
        self.topics_set = set()
        self.persons_set = set()
    
    def load_data(self):
        # Get the document, process the data
        document = BeautifulSoup(urllib2.urlopen("http://eventseer.net/" + self.entity_id).read())
        self._process_cfp(document)
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
        return 'event_' + self.entity_id[2:]
    
    def get_topics(self):
        '''
        Return the set of topics related to this event
        '''
        return self.topics_set
        
    def get_persons(self):
        '''
        Return the set of persons related to this event
        '''
        return self.persons_set
    
    def get_cfp_data(self):
        '''
        Return the CFP data
        '''
        return self.cfp_data
        
    def get_rdf_data(self):
        '''
        Return the content of the RDF graph
        '''
        return self.rdf_data
    
    def _process_cfp(self, document):
        '''
        Get the CFP out of a event page
        @param document: the DOM document of the event
        '''
        # Try to get the cfp
        cfp = document.find(id='cfp-content')
        if cfp == None:
            return
        
        # Process it to remove the markup
        self.cfp_data = cfp.renderContents()
        self.cfp_data = self.cfp_data.replace('<p>', '\n').replace('</p>', '')
        self.cfp_data = self.cfp_data.replace('<br />', '')
        self.cfp_data = self.cfp_data.replace('&nbsp;', ' ')
        self.cfp_data = self.cfp_data.replace('<ul>', '\n').replace('</ul>', '')
        self.cfp_data = re.sub(r'</?(h[1-6]|li)>', '', self.cfp_data, flags=re.IGNORECASE)
        self.cfp_data = re.sub(r'<a [^>]*>([^<]*)</a>', '\g<1>', self.cfp_data, flags=re.IGNORECASE)
        self.cfp_data = re.sub(r'^\n*', '', self.cfp_data, flags=re.IGNORECASE)
        
    def _process_data(self, document):
        '''
        Creates the RDF graph describing the event
        @param document: the DOM document of the event
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
        resource_event = LDES[self.get_resource_name()]
        graph.add((resource_event, RDF.type, SWC['AcademicEvent']))
        
        # Get the title
        if document.find(id='inner_left') != None:
            title = document.find(id='inner_left').find('h1').text
            graph.add((resource_event, RDFS.label, Literal(title)))
          
        # Get the location
        if document.find(text='City:') != None and document.find(text='Country:') != None:
            city = document.find(text='City:').findParent().findNextSibling().renderContents()
            country = document.find(text='Country:').findParent().findNextSibling().renderContents()
            location = get_location(city, country)
            if location == None:
                location = Literal("%s, %s" % (city, country))
            graph.add((resource_event, FOAF['based_near'], location))
        
        # Get the starting and ending dates
        if document.find(text='Period:') != None:
            text = document.find(text='Period:').findParent().findNextSibling().renderContents()
            parts = re.search('(?P<begin>[^-,]*)(-(?P<end>[^,]*))?, (?P<year>\d{4})', text).groupdict()
            if parts['begin'] != None and parts['year'] != None:
                (month, start_day) = parts['begin'].split(' ')
                begin_date = datetime.strptime("%s %s %s" % (start_day, month, parts['year']), "%d %B %Y")
                graph.add((resource_event, ICAL['dtstart'], Literal(begin_date)))
                if parts['end'] != None:
                    end_parts = parts['end'].split(' ')
                    end_date = None
                    if len(end_parts) == 2:
                        end_date = datetime.strptime("%s %s %s" % (end_parts[1], end_parts[0], parts['year']), "%d %B %Y")
                    elif len(end_parts) == 1:
                        end_date = datetime.strptime("%s %s %s" % (end_parts[0], month, parts['year']), "%d %B %Y")
                    if end_date != None:
                        graph.add((resource_event, ICAL['dtend'], Literal(end_date)))
                    
        # Get the data for the CFP
        resource_cfp = LDES[self.get_resource_name() + "_cfp"] 
        graph.add((resource_cfp, RDF.type, CFP['CallForPapers']))
        graph.add((resource_cfp, CFP['for'], LDES[self.entity_id]))
        graph.add((resource_cfp, CFP['details'], URIRef(BASE + 'data/' + self.get_resource_name() + '_cfp.txt')))
        
        # Get the deadlines 
        deadlines = []
        for a in document.findAll('script'):
            res = re.search('var deadlineList = ([^;]*);', a.renderContents())
            if res != None:
                txt = res.group(1).replace('\n', '').replace('\t', '').replace("'", '"')
                txt = re.sub(r'<span [^>]*>([^<]*)</span>', '\g<1>', txt, flags=re.IGNORECASE)
                txt = txt.replace('Date:', '"Date":').replace('Title:', '"Title":')
                deadlines = json.loads(txt)
        i = 0
        for deadline in deadlines:
            resource_deadline = LDES[self.get_resource_name() + '_deadline_' + str(i)]
            graph.add((resource_deadline, RDF.type, ICAL['Vevent']))
            graph.add((resource_deadline, ICAL['dtstart'], Literal(datetime.strptime(deadline['Date'], "%d %b %Y"))))
            graph.add((resource_deadline, ICAL['dtend'], Literal(datetime.strptime(deadline['Date'], "%d %b %Y"))))
            graph.add((resource_deadline, ICAL['summary'], Literal(deadline['Title'])))
            graph.add((resource_deadline, ICAL['relatedTo'], resource_event))
            i = i + 1
            
        # Add the topics and persons
        if document.find(id='cfp-content') != None:
            for link in document.find(id='cfp-content').findAll('a'):
                link = link.get('href')
                if link != None:
                    if link[:3] == '/t/' and link not in self.topics_set:
                        try:
                            graph.add((resource_event, DCT['subject'], LDES[Topic(link[1:-1]).get_resource_name()]))
                            self.topics_set.add(link[1:-1])
                        except:
                            # Ignore bad topic links
                            pass
                    if link[:3] == '/p/' and link not in self.persons_set:
                        try:
                            graph.add((resource_event, LODE['involvedAgent'], LDES[Person(link[1:-1]).get_resource_name()]))
                            self.persons_set.add(link[1:-1])
                        except:
                            # Ignore bad person link
                            pass
        
        # Set the last modification date
        graph.add((self.get_named_graph(), DCT['modified'], Literal(datetime.now()))) 
        
        # Save the data
        self.rdf_data = graph.serialize()

