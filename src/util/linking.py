'''
Created on Mar 23, 2011

@author: cgueret
'''
from SPARQLWrapper import SPARQLWrapper, JSON #@UnresolvedImport

def get_location(city, country):
    sparql = SPARQLWrapper("http://linkedgeodata.org/sparql")
    sparql.setReturnFormat(JSON)

    try:
        # Try if we are lucky
        query = """
        Select ?r From <http://linkedgeodata.org> { 
            ?r <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://linkedgeodata.org/ontology/Place>.
            ?r <http://www.w3.org/2000/01/rdf-schema#label> "%s"@en.
        }
        """ % city
        sparql.setQuery(query)
        results = sparql.query().convert()
        resources = [result["r"]["value"] for result in results["results"]["bindings"]]
        if len(resources) == 1:
            return resources[0]
        
        # Test a bit broader
        query = """
        Select * From <http://linkedgeodata.org> { 
            ?r <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?t.
            ?r <http://www.w3.org/2000/01/rdf-schema#label> "%s"@en.
            OPTIONAL {
                ?r <http://linkedgeodata.org/property/is_in> ?in.
            }
            OPTIONAL {
                ?r <http://linkedgeodata.org/property/is_in%%3Acountry> ?country.
            }
            Filter (?t = <http://linkedgeodata.org/ontology/City> || ?t = <http://linkedgeodata.org/ontology/Town> )
            Filter (bound(?in) && regex(?in, "%s", "i") || !bound(?in))
            Filter (bound(?country) && regex(?country, "%s", "i") || !bound(?country))
            Filter (bound(?in) || bound(?country))
        }
        """ % (city, country, country)
        sparql.setQuery(query)
        results = sparql.query().convert()
        resources = [result["r"]["value"] for result in results["results"]["bindings"]]
        if len(resources) == 1:
            return resources[0]
        
        # Without the language tag
        query = """
        Select ?r From <http://linkedgeodata.org> { 
            ?r <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?t.
            ?r <http://www.w3.org/2000/01/rdf-schema#label> "%s".
            OPTIONAL {
                ?r <http://linkedgeodata.org/property/is_in> ?in.
            }
            OPTIONAL {
                ?r <http://linkedgeodata.org/property/is_in%%3Acountry> ?country.
            }
            Filter (?t = <http://linkedgeodata.org/ontology/City> || ?t = <http://linkedgeodata.org/ontology/Town> )
            Filter (bound(?in) && regex(?in, "%s", "i") || !bound(?in))
            Filter (bound(?country) && regex(?country, "%s", "i")|| !bound(?country))
            Filter (bound(?in) || bound(?country))
        }
        """ % (city, country, country)
        sparql.setQuery(query)
        results = sparql.query().convert()
        resources = [result["r"]["value"] for result in results["results"]["bindings"]]
        if len(resources) == 1:
            return resources[0]
    except:
        # If everything goes wrong, just leave it
        pass
    
    return None
