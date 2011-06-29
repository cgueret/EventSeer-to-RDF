'''
Created on 29 Jun 2011

@author: cgueret
'''
import json
import urllib2
import re
from datetime import datetime
from objects.events import Event
from SPARQLWrapper import SPARQLWrapper, JSON #@UnresolvedImport

class Harvester(object):
    '''
    The Harvester get the list of events from 
    EventSeer using the JSON API and save the 
    data into the triple store
    '''
    def __init__(self, triple_store, data_directory):
        '''
        Constructor
        '''
        self.sparql = SPARQLWrapper(triple_store)
        self.sparql.setReturnFormat(JSON)
        self.data_directory = data_directory
        
    def process_events(self):
        '''
        Call the main API and process all the events, page by page
        '''
        # Number of events to ask at once
        PAGE_SIZE = 10
        
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
        server_version_date = None
        self.sparql.setQuery('select ?d where { <%s> <http://purl.org/dc/terms/modified> ?d}' % event.get_named_graph())
        results = self.sparql.query().convert()
        d = [result["d"]["value"] for result in results["results"]["bindings"]]
        if len(d) == 1:
            server_version_date = d[0]
        
        # Check if the event need to be saved
        save_event = False
        if server_version_date == None:
            # The event is not in the triple store
            print '\t[GEN] %s - %s' % (event_id, event_name)
            save_event = True
        else:
            delta = server_version_date - event_last_update_date
            if delta.days > 0:
                # The event needs to be updated
                print '\t[UPD] %s - %s' % (event_id, event_name)
                save_event = True
            else:
                # The server version is up to date
                print '\t[OK] %s - %s' % (event_id, event_name)
        
        # If needed, process and save the event
        if save_event:
            event.load_data()
                
                 
        # If not existent, generate
        #if not os.path.isfile('data/' + event_id + '.rdf'):
        #    print '\t[GEN] %s - %s' % (event_id, event_name)
        #    event = Event(record)
        #    event.process()
        #    del event
        #    return
        
        # If updated, update
        #last_modification = datetime.strptime(record['Date'], "%d %b %Y")
        #if os.path.isfile('data/' + event_id + '.rdf'):
        #    fileage = datetime.fromtimestamp(os.stat('data/' + event_id + '.rdf').st_mtime)
        #    delta = last_modification - fileage
        #    if delta.days > 0:
        #        print '\t[UPD] %s - %s' % (event_id, event_name)
        #        event = Event(record)
        #        event.process()
        #        del event
        #        return

        #print '\t[OK] %s - %s' % (event_id, event_name)
        
    def _get_events(self, start, size):
        '''
        Return a list of events as a JSON object
        @param start: start index
        @param size: number of events to retrieve
        '''
        url = "http://eventseer.net/e/_category_list_json/?category=e&sort=Date&dir=desc&type=cat&filter=all&deadlines=all&search=text&start=%d&results=%d" % (start, size)
        return json.loads(urllib2.urlopen(url).read())        
                