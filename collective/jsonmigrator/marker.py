from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import defaultMatcher
from collective.transmogrifier.utils import Condition
from zope.dottedname.resolve import resolve
from Products.Five.utilities.marker import mark

import logging

class MarkerSection(object):
    classProvides(ISectionBlueprint)
    implements(ISection)
    """ sets a marker interface on the object under the specified conditions"""
    
    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.context = transmogrifier.context
        self.name = name
        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')
        
        self.interface = options['interface']
        self.condition = Condition(options.get('condition', 'python:True'),
                                   transmogrifier, name, options)
                                   
        logging.getLogger("jsonmigrator.marker").setLevel(logging.WARNING)
    
    def __iter__(self):
        for item in self.previous:
            if not self.condition(item):
                logging.getLogger("jsonmigrator.marker").debug("Condition not satisfied")
                yield item
                continue
            
            pathkey = self.pathkey(*item.keys())[0]
            # not enough info
            if not pathkey:
                logging.getLogger("jsonmigrator.marker").debug("Path not supplied")
                yield item
                continue

            path = item[pathkey]
            ## Skip the Plone site object itself
            #if not path:
                #yield item
                #continue

            obj = self.context.unrestrictedTraverse(
                path.encode().lstrip('/'), None)

            # path doesn't exist
            if obj is None:
                logging.getLogger("jsonmigrator.marker").debug("No object at path")
                yield item
                continue

            interface_name = self.interface
            if interface_name is None:
                logging.getLogger("jsonmigrator.marker").warning("interface option not set")
                yield item
                continue
            
            try:
                interface_class = resolve(interface_name)
                mark(obj, interface_class)
            except Exception, e:
                logging.getLogger("jsonmigrator.marker").error("Error setting interface %s", str(e))
                pass

            yield item
