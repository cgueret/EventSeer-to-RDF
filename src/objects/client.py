'''
Created on Apr 12, 2011

@author: cgueret
'''
import json
import urllib2
import re
from datetime import datetime
from rdflib import Graph
from objects import DCT
from objects.topics import Topic
from objects.events import Event
import os
import isodate


class Client(object):
    # URLs of the JSON API for EventSeer
    JSON_API = {
        'Event' : 'http://eventseer.net/e/_category_list_json/?category=e&sort=Date&dir=desc&type=cat&filter=all&deadlines=all&search=text&start=%d&results=%d',
        'Topic' : 'http://eventseer.net/t/_category_list_json/?category=t&sort=Topic&dir=desc&type=cat&filter=all&search=text&start=%d&results=%d'
    }
    
    # Number of events to ask at once
    PAGE_SIZE = 5 # 100
        
    '''
    This class is a wrapper for all the topics contained on EventSeer.
    It queries the service, creates instances of Topic and saves the data on the disk
    '''
    def process(self, type):
        '''
        Call the JSON API and process all the records, page by page
        '''
        # Get the first entry to see how many there are
        obj = self._get_page(type, 0, 1)
        #pages = (obj['totalRecords'] / self.PAGE_SIZE) + 1
        pages = 1
        del obj
        
        # Open the ZIP file in the data directory
        #self.zip_container = ZipFile('data/%ss.zip' % type, 'a')
        
        # Iterate over all the pages
        for i in range(0, pages): 
            # Load the page
            print 'Get page %d' % i
            page = self._get_page(type, i * self.PAGE_SIZE, self.PAGE_SIZE)
            
            # Process the records
            for record in page['records']:
                self._process_record(record, type)
            
        # Close the ZIP file
        #self.zip_container.close()
        
    def _get_page(self, type, start, size):
        '''
        Return a page of records as a JSON object
        @param type: the type of records
        @param start: start index
        @param size: number of records
        '''
        url = self.JSON_API[type] % (start, size)
        return json.loads(urllib2.urlopen(url).read())        

    def _process_record(self, record, type):
        '''
        Process a specific record
        '''
        # Compose a name and an ID for the record
        entity_name = re.sub(r'<a [^>]*>([^<]*)</a>', '\g<1>', record[type]).replace('\n', '')
        entity_url = re.search('href="([^"]*)"', record[type]).group(1) 
        entity_id = entity_url.replace('/', '')
        if type == 'Topic':
            entity_id = entity_id.replace('t', 'topic_')
            entity = Topic(entity_name, entity_id)
        if type == 'Event':
            entity_id = entity_id.replace('e', 'event_')
            entity = Event(entity_name, entity_id)
        rdf_file = '%s.rdf' % entity_id
        named_graph_resource = entity.named_graph()
        
        # Open the file in the container and get last modification date
        last_modification = None
        if os.path.isfile('data/' + rdf_file):# in self.zip_container.namelist():
            #data = self.zip_container.read(rdf_file)
            g = Graph()
            g.parse('data/' + rdf_file, format='xml')
            for _, _, date in g.triples((named_graph_resource, DCT['modified'], None)):
                last_modification = isodate.parse_datetime(date)
                
        # If not existent or out dated, generate
        generate = False
        if last_modification == None:
            # If not existent, generate
            print '\t[GEN] %s - %s' % (entity_id, entity_name)
            generate = True
        else:
            delta = datetime.strptime(record['Date'], "%d %b %Y") - last_modification
            if delta.days > 0:
                # If updated, update
                print '\t[UPD] %s - %s' % (entity_id, entity_name)
                generate = True
                        
        if not generate:
            print '\t[OK] %s - %s' % (entity_id, entity_name)
            return
        
        # Process a topic
        if type == 'Topic':
            print record
            pass
        
        # Process an event
        if type == 'Event':
            entity.parse(record, entity_url)
            # Save the CFP
            f = open('data/' + entity_id + '_cfp.txt', 'w')
            f.write(entity.get_cfp_data())
            f.close()

        # Save the RDF data
        f = open('data/' + rdf_file, 'w')
        f.write(entity.get_rdf_data())
        f.close()
        
        # TODO process the list of cited topics, events and organizations
        
        #self.zip_container.writestr(rdf_file, entity.get_rdf_data())
            