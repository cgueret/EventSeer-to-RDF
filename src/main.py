'''
Created on Mar 24, 2011

@author: cgueret
'''
#from objects.events import Events #@UnusedImport
#from util.synchronize import TripleStore #@UnusedImport
#from objects.client import Client
from objects.topics import Topic
from harvester.harvester import Harvester
from objects.persons import Person

if __name__ == '__main__':
    harvester = Harvester("http://eculture2.cs.vu.nl:8890", "data/")
    harvester.process_events()
    
    #topic = Topic('t/data_analysis')
    #topic.load_data()
    #print topic.get_rdf_data()
    
    #person = Person('p/pieter_de_leenheer')
    #person.load_data()
    #print person.get_rdf_data()
    
    #event = Event('e/16445')
    #event = Event('e/16589')
    
