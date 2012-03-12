import base64
from zope.interface import implements
from zope.interface import classProvides
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from Products.Archetypes.interfaces import IBaseObject

import logging

class DataFields(object):
    """
    """

    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.context = transmogrifier.context
        self.datafield_prefix = options.get('datafield-prefix', '_datafield_')
        self.root_path_length = len(self.context.getPhysicalPath())


    def __iter__(self):
        for item in self.previous:

            # not enough info
            if '_path' not in item:
                logging.getLogger("jsonmigrator.datafields").info("Path not in item")
                yield item
                continue

            obj = self.context.unrestrictedTraverse(
                        item['_path'].lstrip('/'), None)

            # path doesn't exist
            if obj is None:
                logging.getLogger("jsonmigrator.datafields").info("Path doesn't exist in %s %s" %
                                                                  (self.context, item['_path']))
                yield item
                continue

            # do nothing if we got a wrong object through acquisition
            path = item['_path']
            if path.startswith('/'):
                path = path[1:]
            if '/'.join(obj.getPhysicalPath()[self.root_path_length:]) != path:
                logging.getLogger("jsonmigrator.datafields").info("Wrong object got thru acquisition \nobject: %s, \nitem path: %s" %
                                                                  ('/'.join(obj.getPhysicalPath()[self.root_path_length:]),
                                                                   path))
                yield item
                continue

            if IBaseObject.providedBy(obj):
                for key in item.keys():

                    if not key.startswith(self.datafield_prefix):
                        continue

                    fieldname = key[len(self.datafield_prefix):]
                    #logging.getLogger("jsonmigrator.datafields").info("Decoding field %s" % (fieldname))
                    field = obj.getField(fieldname)
                    if field is None:
                        continue
                    value = base64.b64decode(item[key]['data'])

                    # XXX: handle other data field implementations
                    old_value = field.get(obj).data
                    if value != old_value:
                        field.set(obj, value)
                        filename = item[key]['filename']
                        if isinstance( filename, unicode):
                            filename = filename.encode('utf-8')
                        obj.setFilename(filename)
                        obj.setContentType(item[key]['content_type'])

            yield item

