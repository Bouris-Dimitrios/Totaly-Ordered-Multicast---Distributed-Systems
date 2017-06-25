'''
Created on Nov 6, 2015

@author: jimbouris
'''

class MyClass(object):
    '''
    classdocs
    '''
class AsciiUtilities(object):
    @staticmethod
    def getasciiValue(asciiInt):
        return str(unichr(asciiInt))
        