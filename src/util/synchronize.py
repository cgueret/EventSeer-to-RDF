'''
Created on Mar 24, 2011

@author: cgueret
'''
import os
from datetime import datetime
from SPARQLWrapper import SPARQLWrapper, JSON #@UnresolvedImport
from objects import BASE
import pycurl

class TripleStore(object):
    '''
    Interface to a triple store that supports named graphs
    '''
    def __init__(self, url, data):
        '''
        Constructor
        @param url: the HTTP address of the triple store
        @param data: the folder where all the triples are stored
        '''
        self.url = url
        self.data = data
        self.sparql = SPARQLWrapper(url + "sparql/")
        self.sparql.setReturnFormat(JSON)


    def run(self):
        '''
        Go through all the files in the data folder and update them on the triple store if needed
        '''
        for file in os.listdir(self.data):
            # Skip non RDF file
            if not file.endswith('rdf'):
                continue
            
            # Get the last time the file was sent to the server
            last_modification = None
            resource = BASE + 'data/' + file
            self.sparql.setQuery('select ?d where { <%s> <http://purl.org/dc/terms/modified> ?d}' % resource)
            results = self.sparql.query().convert()
            d = [result["d"]["value"] for result in results["results"]["bindings"]]
            if len(d) == 1:
                last_modification = d[0]
    
            # Get the last time the RDF was modified
            file_age = datetime.fromtimestamp(os.stat(self.data + file).st_mtime)
       
            # If the file is more recent locally, re-upload it
            if (last_modification == None) or (file_age - last_modification > 0):
                c = pycurl.Curl()
                c.setopt(pycurl.URL, self.url + 'data/' + resource)
                c.setopt(pycurl.UPLOAD, 1)
                c.setopt(pycurl.READFUNCTION, open(self.data + file, 'rb').read)
                c.setopt(pycurl.INFILESIZE, os.path.getsize(self.data + file))
                c.perform()
                c.close()
                
