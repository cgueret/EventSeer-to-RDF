'''
Created on Mar 24, 2011

@author: cgueret
'''
import json
import urllib2
import re
import os
from BeautifulSoup import BeautifulSoup
from rdflib import ConjunctiveGraph, Literal, RDF, URIRef
from datetime import datetime
from objects import SWC, CFP, ICAL, FOAF, DCT, LODE, LDES, BASE, \
    NAMED_GRAPHS_BASE
from util.linking import get_location

class Events(object):
    '''
    This class is a wrapper for all the events contained on EventSeer.
    It queries the service, creates instances of Event and saves the data on the disk
    '''
    def process(self):
        '''
        Call the main API and process all the events, page by page
        '''
        # Number of events to ask at once
        PAGE_SIZE = 100

        # Iterate over all the events
        obj = self._get_events(0, 1)
        for i in range(0, (obj['totalRecords'] / PAGE_SIZE) + 1):
            # Load the page
            print 'Get page %d' % i
            page = self._get_events(i * PAGE_SIZE, PAGE_SIZE)
            for record in page['records']:
                self._process_record(record)

    def _get_events(self, start, size):
        '''
        Return a list of event as a JSON object
        @param start: start index
        @param size: number of events to retrieve
        '''
        url = "http://eventseer.net/e/_category_list_json/?category=e&sort=Date&dir=desc&type=cat&dom_id=e_table&filter=all&deadlines=all&search=text&country=0&region=0&city=0&start=%d&results=%d" % (start, size)
        return json.loads(urllib2.urlopen(url).read())        

    def _process_record(self, record):
        event_name = re.sub(r'<a [^>]*>([^<]*)</a>', '\g<1>', record['Event'], flags=re.IGNORECASE).replace('\n', '')
        event_id = re.search('href="([^"]*)"', record['Event']).group(1).replace('/', '').replace('e', 'event_')
        
        # If not existent, generate
        if not os.path.isfile('data/' + event_id + '.rdf'):
            print '\t[GEN] %s - %s' % (event_id, event_name)
            event = Event(record)
            event.process()
            del event
            return
        
        # If updated, update
        last_modification = datetime.strptime(record['Date'], "%d %b %Y")
        if os.path.isfile('data/' + event_id + '.rdf'):
            fileage = datetime.fromtimestamp(os.stat('data/' + event_id + '.rdf').st_mtime)
            delta = last_modification - fileage
            if delta.days > 0:
                print '\t[UPD] %s - %s' % (event_id, event_name)
                event = Event(record)
                event.process()
                del event
                return

        print '\t[OK] %s - %s' % (event_id, event_name)
        

class Event(object):
    def __init__(self, entity_id):
        '''
        Constructor 
        @param entity_id: an event id such as 'e/16589'
        '''
        # Keep track of the ID
        self.entity_id = entity_id

        # Containers for the data 
        self.cfp_data = None
        self.rdf_data = None
        
        # Set of cited persons and topics
        self.topics_set = set()
        self.persons_set = set()
        
        # Get the document
        document = BeautifulSoup(urllib2.urlopen("http://eventseer.net/" + entity_id).read())
        print "http://eventseer.net/" + entity_id
        
        # Process the data
        self._process_cfp(document)
        self._process_data(document)
         
    def get_named_graph(self):
        '''
        Return the named graph for storing the data
        '''
        return URIRef(NAMED_GRAPHS_BASE + self.entity_id + '.rdf')
    
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
        resource_event = LDES[self.entity_id]
        graph.add((resource_event, RDF.type, SWC['AcademicEvent']))
        
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
            (month, day, year) = text.split(' ')
            days = day[:-1].split('-')
            begin = datetime.strptime("%s %s %s" % (days[0], month, year), "%d %B %Y")
            graph.add((resource_event, ICAL['dtstart'], Literal(begin)))
            if len(days) == 2:
                end = datetime.strptime("%s %s %s" % (days[1], month, year), "%d %B %Y")
                graph.add((resource_event, ICAL['dtend'], Literal(end)))
                    
        # Get the data for the CFP
        graph.add((LDES[self.entity_id + '_cfp'], RDF.type, CFP['CallForPapers']))
        graph.add((LDES[self.entity_id + '_cfp'], CFP['for'], LDES[self.entity_id]))
        graph.add((LDES[self.entity_id + '_cfp'], CFP['details'], URIRef(BASE + 'data/' + self.entity_id + '_cfp.txt')))
        
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
            resource_deadline = LDES[self.entity_id + '_deadline-' + str(i)]
            graph.add((resource_deadline, RDF.type, ICAL['Vevent']))
            graph.add((resource_deadline, ICAL['dtstart'], Literal(datetime.strptime(deadline['Date'], "%d %b %Y"))))
            graph.add((resource_deadline, ICAL['dtend'], Literal(datetime.strptime(deadline['Date'], "%d %b %Y"))))
            graph.add((resource_deadline, ICAL['summary'], Literal(deadline['Title'])))
            graph.add((resource_deadline, ICAL['relatedTo'], resource_event))
            i = i + 1
            
        # Add the topics and persons
        for link in document.find(id='cfp-content').findAll('a'):
            link = link.get('href')
            if link != None:
                if link[:3] == '/t/' and link not in self.topics_set:
                    self.topics_set.add(link)
                    topic_id = 'topic_' + link[3:-1]
                    graph.add((resource_event, DCT['subject'], LDES[topic_id]))
                if link[:3] == '/p/' and link not in self.persons_set:
                    self.persons_set.add(link)
                    person_id = 'person_' + link[3:-1]
                    graph.add((resource_event, LODE['involvedAgent'], LDES[person_id]))
        
        # Set the last modification date
        graph.add((self.get_named_graph(), DCT['modified'], Literal(datetime.now()))) 
        
        # Save the data
        self.rdf_data = graph.serialize()

