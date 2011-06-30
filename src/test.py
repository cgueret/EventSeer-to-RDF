'''
Created on 30 Jun 2011

@author: cgueret
'''
import re

if __name__ == '__main__':
    dates = {'August 24-26, 2011','October 31-November 3, 2011', 'September 5, 2011'}
    for d in dates:
        print d
        parts = re.search('(?P<begin>[^-,]*)(-(?P<end>[^,]*))?, (?P<year>\d{4})', d).groupdict()
        print parts
        if 'begin' in parts:
            print parts['begin']