'''
Created on 29 Jun 2011

@author: cgueret
'''
import json
import urllib2
import re
from datetime import datetime
from objects.events import Event
from util.triplestore import TripleStore
from objects.topics import Topic
from objects.persons import Person


class Harvester(object):
    '''
    The Harvester get the list of events from 
    EventSeer using the JSON API and save the 
    data into the triple store
    '''
    def __init__(self, triple_store_url, data_directory):
        '''
        Constructor
        '''
        self.triple_store = TripleStore(triple_store_url)
        self.data_directory = data_directory
        
    def process_events(self):
        '''
        Call the main API and process all the events, page by page
        '''
        # Number of events to ask at once
        PAGE_SIZE = 5
        
        # Iterate over all the pages of events
        #pages = (self._get_events(0, 1)['totalRecords'] / PAGE_SIZE) + 1
        pages = 1
        for i in range(0, pages):
            print 'Get page %d' % i
            page = self._get_events(i * PAGE_SIZE, PAGE_SIZE)
            for record in page['records']:
                self._process_event(record)

    def _process_event(self, record):
        # Get the event id, its name and its last modification date 
        event_name = re.sub(r'<a [^>]*>([^<]*)</a>', '\g<1>', record['Event'], flags=re.IGNORECASE).replace('\n', '')
        event_id = re.search('href="([^"]*)"', record['Event']).group(1)[1:-1]
        event_last_update_date = datetime.strptime(record['Date'], "%d %b %Y")
        event = Event(event_id)
        
        # Get the last modification date from the end point
        server_version_date = self.triple_store.get_last_version_date(event)
        server_version_date = None
        
        # Check the status of the event in the triple store
        if server_version_date == None or (event_last_update_date - server_version_date).days > 0:
            # The event is not in the triple store or needs to be updated
            print '\t[UPD] %s - %s' % (event_id, event_name)
            
            # Save the RDF data of the event
            event.load_data()
            self.triple_store.save_rdf_data(event)
            
            # Save the CFP from the call    
            file = open(self.data_directory + '/' + event.get_resource_name() + '_cfp.txt', 'w')
            file.write(event.get_cfp_data())
            file.close()
            
            # Add the topics not already existing
            for t in event.get_topics():
                topic = Topic(t)
                if self.triple_store.get_last_version_date(topic) == None:
                    print '\t\t[UPD-TOPIC] %s' % t
                    topic.load_data()
                    self.triple_store.save_rdf_data(topic)
            
            # Update the data about all the persons concerned
            for p in event.get_persons():
                print '\t\t[UPD-PERSON] %s' % p
                person = Person(p)
                person.load_data()
                self.triple_store.save_rdf_data(person)
            
        else:
            # The server version is up to date
            print '\t[OK] %s - %s' % (event_id, event_name)
        
    def _get_events(self, start, size):
        '''
        Return a list of events as a JSON object
        @param start: start index
        @param size: number of events to retrieve
        '''
        url = "http://eventseer.net/e/_category_list_json/?category=e&sort=Date&dir=desc&type=cat&filter=all&deadlines=all&search=text&start=%d&results=%d" % (start, size)
        return json.loads(urllib2.urlopen(url).read())        
                