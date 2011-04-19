'''
Created on Mar 22, 2011

@author: cgueret
'''
import json
import urllib2
import pprint
import re
import os
from BeautifulSoup import BeautifulSoup
from rdflib import ConjunctiveGraph, Literal, RDF, URIRef, Namespace
from datetime import datetime
from util.linking import get_location

PAGE_SIZE = 100
PP = pprint.PrettyPrinter(indent=4)
BASE = 'http://linkeddata.few.vu.nl/eventseer/'
LDES = Namespace(BASE + "resource/")
SWRC = Namespace("http://swrc.ontoware.org/ontology#")
SWC = Namespace("http://data.semanticweb.org/ns/swc/ontology#")
CFP = Namespace("http://sw.deri.org/2005/08/conf/cfp.owl#")
ICAL = Namespace("http://www.w3.org/2002/12/cal/ical#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
DCT = Namespace("http://purl.org/dc/terms/")
LODE = Namespace("http://linkedevents.org/ontology/")

def get_events_json(start, size):
    url = "http://eventseer.net/e/_category_list_json/?category=e&q=&sort=Date&dir=desc&type=cat&dom_id=e_table&filter=all&deadlines=all&search=text&country=0&region=0&city=0&datarec=&startdate=&start=%d&results=%d" % (start, size)
    return json.loads(urllib2.urlopen(url).read())

def process_event(event):
    # Get the event page and compute its id
    url = re.search('href="([^"]*)"', event['Event']).group(1)
    event_id = url.replace('/', '').replace('e', 'event_')
    
    # Convert the CFP to text and save it
    document = BeautifulSoup(urllib2.urlopen("http://eventseer.net" + url).read())
    if document.find(id='cfp-content') == None:
        return
    cfp = document.find(id='cfp-content').renderContents()
    cfp = cfp.replace('<p>', '\n').replace('</p>', '').replace('<br />', '')
    cfp = cfp.replace('<ul>', '\n').replace('</ul>', '').replace('<li>', '').replace('</li>', '')
    cfp = re.sub(r'<a [^>]*>([^<]*)</a>', '\g<1>', cfp, flags=re.IGNORECASE)
    cfp = re.sub(r'^\n*', '', cfp, flags=re.IGNORECASE)
    f = open('data/' + event_id + '_cfp.txt', 'w')
    f.write(cfp)
    f.close()

    # Create, populate and save the RDF graph
    graph = ConjunctiveGraph()
    graph.bind('swc', SWC)
    graph.bind('cfp', CFP)
    graph.bind('ical', ICAL)
    graph.bind('foaf', FOAF)
    graph.bind('dct', DCT)
    graph.bind('lode', LODE)
    ### Event
    resource_event = LDES[event_id]
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
    ### CFP
    resource_cfp = LDES[event_id + '_cfp']
    graph.add((resource_cfp, RDF.type, CFP['CallForPapers']))
    graph.add((resource_cfp, CFP['for'], resource_event))
    graph.add((resource_cfp, CFP['details'], URIRef(BASE + 'data/' + event_id + '_cfp.txt')))
    ### Deadlines
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
        resource_deadline = LDES[event_id + '_deadline-' + str(i)]
        graph.add((resource_deadline, RDF.type, ICAL['Vevent']))
        graph.add((resource_deadline, ICAL['dtstart'], Literal(datetime.strptime(deadline['Date'], "%d %b %Y"))))
        graph.add((resource_deadline, ICAL['dtend'], Literal(datetime.strptime(deadline['Date'], "%d %b %Y"))))
        graph.add((resource_deadline, ICAL['summary'], Literal(deadline['Title'])))
        graph.add((resource_deadline, ICAL['relatedTo'], resource_event))
        i = i + 1
    ### Topics and persons
    for link in document.find(id='cfp-content').findAll('a'):
        link = link.get('href')
        if link != None:
            if link[:3] == '/t/':
                topic_id = link.replace('/t/', 'topic_').replace('/', '')
                graph.add((resource_event, DCT['subject'], LDES[topic_id]))
            if link[:3] == '/p/':
                person_id = link.replace('/p/', 'person_').replace('/', '')
                graph.add((resource_event, LODE['involvedAgent'], LDES[person_id]))
    ### Save
    f = open('data/' + event_id + '.rdf', 'w')
    f.write(graph.serialize())
    f.close()
    
    
    # TODO In web service, export event deadlines in ICAL

def process_events():
    # Iterate over all the events
    obj = get_events_json(0, 1)
    for i in range(0, (obj['totalRecords'] / PAGE_SIZE) + 1):
        # Load the page
        print 'Get page %d' % i
        page = get_events_json(i * PAGE_SIZE, PAGE_SIZE)
        for record in page['records']:
            event_name = re.sub(r'<a [^>]*>([^<]*)</a>', '\g<1>', record['Event'], flags=re.IGNORECASE).replace('\n', '')
            event_id = re.search('href="([^"]*)"', record['Event']).group(1).replace('/', '').replace('e', 'event_')
            
            # If not existent, generate
            if not os.path.isfile('data/' + event_id + '.rdf'):
                print '\t[GEN] %s - %s' % (event_id, event_name)
                process_event(record)
                continue
            
            # If updated, update
            last_modification = datetime.strptime(record['Date'], "%d %b %Y")
            if os.path.isfile('data/' + event_id + '.rdf'):
                fileage = datetime.fromtimestamp(os.stat('data/' + event_id + '.rdf').st_mtime)
                delta = last_modification - fileage
                if delta.days > 0:
                    print '\t[UPD] %s - %s' % (event_id, event_name)
                    process_event(record)
                    continue

            print '\t[OK] %s - %s' % (event_id, event_name)
    
if __name__ == '__main__':
    #print get_location('Banff', 'Canada')
    #print get_location('Vienna', 'Austria')
    #print get_location('Barcelona', 'Spain')
    #print get_location('Melbourne', 'Australia')
    #print get_location('Campus', 'United States')
    #sys.exit()
    process_events()
