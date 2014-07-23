
from zope.interface import implements
from zope.interface import classProvides

from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Matcher
from collective.transmogrifier.utils import defaultKeys

from Products.CMFCore.utils import getToolByName
from Products.Archetypes.interfaces import IBaseObject
# Dexterity Schema
DEXTERITY_INSTALLED = 0
try:
    from plone.directives import form
    DEXTERITY_INSTALLED = 1
except:
    pass

import logging

class Owner(object):
    """ Expects '_owner' to be a userid. Changes ownership to this userid and
        adds 'Owner' to it's roles.
        Also updates creators list to 'creators' key, prefixed by this userid.
    """

    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous
        self.context = transmogrifier.context
        self.memtool = getToolByName(self.context, 'portal_membership')

        if 'path-key' in options:
            pathkeys = options['path-key'].splitlines()
        else:
            pathkeys = defaultKeys(options['blueprint'], name, 'path')
        self.pathkey = Matcher(*pathkeys)

        if 'owner-key' in options:
            ownerkeys = options['owner-key'].splitlines()
        else:
            ownerkeys = defaultKeys(options['blueprint'], name, 'owner')
        self.ownerkey = Matcher(*ownerkeys)

    def __iter__(self):
        for item in self.previous:
            pathkey = self.pathkey(*item.keys())[0]
            ownerkey = self.ownerkey(*item.keys())[0]


            if not pathkey or not ownerkey or \
               ownerkey not in item:    # not enough info
                yield item; continue
            
            if item[ownerkey] is None:
                yield item; continue

            owner_userid = item[ownerkey]
            logging.getLogger("jsonmigrator.owner").debug("owner key is set")

            obj = self.context.unrestrictedTraverse(
                    item[pathkey].lstrip('/'), None)
            if obj is None:
                # path doesn't exist
                yield item; continue

            if not (IBaseObject.providedBy(obj) or (DEXTERITY_INSTALLED and form.Schema.providedBy(obj))):
                # Neither Archetypes or Dexterity installed
                yield item; continue

            # Amendments made here in line with current plone docs
            # http://docs.plone.org/develop/plone/content/ownership.html
            # and this useful blog item
            # http://keeshink.blogspot.co.uk/2010/04/change-creator-programmatically.html
            try:
                owner_obj = self.memtool.getMemberById(owner_userid)
                obj.changeOwnership(owner_obj)
                logging.getLogger("jsonmigrator.owner").debug("Changed ownership to: " + owner_userid)
            except Exception, e:
                raise Exception('ERROR: %s changing ownership of %s to %s' % \
                        (str(e), item[pathkey], owner_userid))

            try:
                roles = list(obj.get_local_roles_for_userid(owner_userid))
                if 'Owner' not in roles:
                    roles.append('Owner')
                    obj.manage_setLocalRoles(owner_userid, roles)
                    logging.getLogger("jsonmigrator.owner").debug("Changed local roles for %s to: %s" % 
                                                                 (owner_userid, roles))
                else:
                    logging.getLogger("jsonmigrator.owner").debug("'Owner' already in local roles for %s" % 
                                                                 (owner_userid))
                    
            except Exception, e:
                raise Exception('ERROR: %s setting local roles %s' % \
                        (str(e), item[pathkey]))

                    
            # Add the new _owner as primary author
            # Assume that creators is not yet set (e.g. by another blueprint) 
            # in the object
            creators = []
            if 'creators' in item:
                creators = item['creators']
                    
                if owner_userid in creators:
                    # Don't add same creator twice, but move to front
                    del creators[creators.index(owner_userid)]
            
            creators.insert(0, owner_userid)
            obj.setCreators(creators)
            logging.getLogger("jsonmigrator.owner").debug("Set creators to: %s" % creators)
    
            yield item
