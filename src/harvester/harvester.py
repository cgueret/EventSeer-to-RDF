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
import pycurl
import cStringIO


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
        self.triple_store = triple_store
        self.sparql = SPARQLWrapper(triple_store + "/sparql")
        self.sparql.setReturnFormat(JSON)
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
        server_version_date = None
        self.sparql.setQuery('select distinct ?d where { <%s> <http://purl.org/dc/terms/modified> ?d}' % event.get_named_graph())
        results = self.sparql.query().convert()
        d = [result["d"]["value"] for result in results["results"]["bindings"]]
        if len(d) == 1:
            server_version_date = datetime.strptime(d[0][:19], "%Y-%m-%dT%H:%M:%S")
            
        # Check if the event need to be saved
        save_event = False
        if server_version_date == None:
            # The event is not in the triple store
            print '\t[GEN] %s - %s' % (event_id, event_name)
            save_event = True
        else:
            delta = event_last_update_date - server_version_date
            if delta.days > 0:
                # The event needs to be updated
                print '\t[UPD] %s - %s' % (event_id, event_name)
                save_event = True
            else:
                # The server version is up to date
                print '\t[OK] %s - %s' % (event_id, event_name)
        
        # If needed, process and save the event
        save_event=True
        if save_event:
            # Get the data
            event.load_data()
            
            # Save the RDF data to the store
            rdf = event.get_rdf_data()
            c = pycurl.Curl()
            target = str(self.triple_store + '/DAV/home/eventseer/rdf_sink/' + event.get_resource_name() + '.rdf')
            c.setopt(pycurl.URL, target)
            c.setopt(pycurl.UPLOAD, 1)
            c.setopt(pycurl.USERAGENT, "eventseer")
            c.setopt(pycurl.USERPWD, "eventseer")
            c.setopt(pycurl.READFUNCTION, cStringIO.StringIO(rdf).read)
            c.setopt(pycurl.INFILESIZE, len(rdf))
            response = cStringIO.StringIO()
            c.setopt(pycurl.WRITEFUNCTION, response.write)
            c.perform()
            c.close()
            
            # Save the CFP from the call    
            file = open(self.data_directory + '/' + event.get_resource_name() + '_cfp.txt', 'w')
            file.write(event.get_cfp_data())
            file.close()
        
    def _get_events(self, start, size):
        '''
        Return a list of events as a JSON object
        @param start: start index
        @param size: number of events to retrieve
        '''
        url = "http://eventseer.net/e/_category_list_json/?category=e&sort=Date&dir=desc&type=cat&filter=all&deadlines=all&search=text&start=%d&results=%d" % (start, size)
        return json.loads(urllib2.urlopen(url).read())        
                