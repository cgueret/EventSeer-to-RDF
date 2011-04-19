'''
Created on Mar 24, 2011

@author: cgueret
'''
from objects.events import Events #@UnusedImport
from util.synchronize import TripleStore #@UnusedImport
from objects.client import Client

if __name__ == '__main__':
    client = Client()
    client.process('Event')
    
    # http://eventseer.net/p/christophe_gueret/
    # http://eventseer.net/t/data_integration/
    # http://eventseer.net/e/7690/
    
    
    # Process all the events
    #events = Events().process()
    #del events
    
    # Synchronize the content of the data folder with the triple store
    #triple_store = TripleStore("http://localhost:9090/", "data/")
    #triple_store.run()
    
