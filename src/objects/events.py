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
    def __init__(self, entity_name, entity_id):
        '''
        Constructor
        '''
        self.event_id = entity_id
        self.rdf_data = None

        # Data for the CFPs         
        self.cfp_data = None
        self.cfp_file = 'data/' + self.event_id + '_cfp.txt'
        
    def parse(self, record, entity_url):
        # Get the document
        document = BeautifulSoup(urllib2.urlopen("http://eventseer.net" + entity_url).read())
        
        # Take care of the CFP
        self._process_cfp(document)
        
        # Take care of all the triples
        self._process_data(record, document)
    
        # TODO return a list of cited topics, people, and organizations
         
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
        
    def get_cfp_data(self):
        return self.cfp_data
        
    def get_rdf_data(self):
        return self.rdf_data
    
    def named_graph(self):
        return URIRef(NAMED_GRAPHS_BASE + self.event_id + '.rdf')
        
    def _process_data(self, event, document):
        '''
        Creates the RDF graph describing the event
        @param event: the JSON description of the event
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
        
        # Add the data for the event
        resource_event = LDES[self.event_id]
        graph.add((resource_event, RDF.type, SWC['AcademicEvent']))
        if event['StartDate'] != None:
            graph.add((resource_event, ICAL['dtstart'], Literal(datetime.strptime(event['StartDate'], "%d %b %Y"))))
        if event['EndDate'] != None:
            graph.add((resource_event, ICAL['dtend'], Literal(datetime.strptime(event['EndDate'], "%d %b %Y"))))
        if event['City'] != None and event['Country'] != None:
            city = get_location(event['City'], event['Country'])
            if city != None:
                city = URIRef(city)
            else:
                city = Literal(event['City'] + ", " + event['Country'])
            graph.add((resource_event, FOAF['based_near'], city))
                    
        # Add the data for the CFP
        resource_cfp = LDES[self.event_id + '_cfp']
        graph.add((resource_cfp, RDF.type, CFP['CallForPapers']))
        graph.add((resource_cfp, CFP['for'], resource_event))
        graph.add((resource_cfp, CFP['details'], URIRef(BASE + 'data/' + self.event_id + '_cfp.txt')))
        
        # Add the deadlines 
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
            resource_deadline = LDES[self.event_id + '_deadline-' + str(i)]
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
                if link[:3] == '/t/':
                    topic_id = link.replace('/t/', 'topic_').replace('/', '')
                    graph.add((resource_event, DCT['subject'], LDES[topic_id]))
                if link[:3] == '/p/':
                    person_id = link.replace('/p/', 'person_').replace('/', '')
                    graph.add((resource_event, LODE['involvedAgent'], LDES[person_id]))
        
        # Set the last modification date
        resource = URIRef(NAMED_GRAPHS_BASE + self.event_id + '.rdf')
        graph.add((resource, DCT['modified'], Literal(datetime.now()))) 
        
        self.rdf_data = graph.serialize()

