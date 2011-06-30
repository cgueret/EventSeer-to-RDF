'''
Created on 30 Jun 2011

@author: cgueret
'''
from SPARQLWrapper import SPARQLWrapper, JSON #@UnresolvedImport
from datetime import datetime
import pycurl
import cStringIO

class TripleStore(object):
    '''
    Interface with a Virtuoso TripleStore
    '''
    def __init__(self, triple_store_url):
        '''
        Constructor
        '''
        self.triple_store_url = triple_store_url
        self.sparql = SPARQLWrapper(self.triple_store_url + "/sparql")
        self.sparql.setReturnFormat(JSON)

    
    def get_last_version_date(self, entity):
        '''
        Get the last modification date from the end point
        '''
        self.sparql.setQuery('select distinct ?d where { <%s> <http://purl.org/dc/terms/modified> ?d}' % entity.get_named_graph())
        results = self.sparql.query().convert()
        d = [result["d"]["value"] for result in results["results"]["bindings"]]
        if len(d) == 1:
            return datetime.strptime(d[0][:19], "%Y-%m-%dT%H:%M:%S")
        else:
            return None

    
    def save_rdf_data(self, entity):
        '''
        Save the RDF data to the store
        '''
        rdf = entity.get_rdf_data()
        c = pycurl.Curl()
        target = str(self.triple_store_url + '/DAV/home/eventseer/rdf_sink/' + entity.get_resource_name() + '.rdf')
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

    
    
    
    
