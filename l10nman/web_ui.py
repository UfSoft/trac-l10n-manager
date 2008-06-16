# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8
# =============================================================================
# $Id$
# =============================================================================
#             $URL$
# $LastChangedDate$
#             $Rev$
#   $LastChangedBy$
# =============================================================================
# Copyright (C) 2008 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# Please view LICENSE for additional licensing information.
# =============================================================================

import re
from cStringIO import StringIO

from genshi.builder import tag

from trac.core import *
from trac.web import IRequestHandler
from trac.web.chrome import ITemplateProvider, INavigationContributor


from trac.mimeview import *
from trac.versioncontrol.web_ui.util import *

from babel.messages.pofile import read_po

from l10nman.model import *


class L10nModule(Component):
    implements(ITemplateProvider, INavigationContributor, IRequestHandler)

    # ITemplateProvider methods
    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('l10nman', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return 'translations'

    def get_navigation_items(self, req):
        yield ('mainnav', 'translations',
               tag.a('Translations', href=req.href.translations()))

    # IRequestHandler methods
    def match_request(self, req):
        match = re.match(r'^/translations(?:/(.*))?', req.path_info)
        if match:
            print match.groups()
            return True

    def process_request(self, req):
        match = re.match(r'^/translations(?:(?P<name>/([^/]*))(?P<path>/(.*)))?', req.path_info)

        db = self.env.get_db_cnx()
        cursor = db.cursor()

        cursor.execute("SELECT locale, fpath, repobase, revision "
                       "FROM l10n_catalogs WHERE id=%s", (1,))
        row = cursor.fetchone()
        print row
        catalog = Catalog(self.env, *row)

        print catalog
        print catalog.messages
#
#        self.log.debug('trying to process request')
#        catalog_path = '/trunk/irssinotifier/i18n/irssinotifier.pot'
#
#        repos = self.env.get_repository(req.authname)
#        revision = repos.youngest_rev
#        node = get_existing_node(self.env, repos, catalog_path, revision)
#        mime_type = node.content_type
#        if not mime_type or mime_type == 'application/octet-stream':
#            mime_type = get_mimetype(node.name) or mime_type or 'text/plain'
#
#        # We don't have to guess if the charset is specified in the
#        # svn:mime-type property
#        ctpos = mime_type.find('charset=')
#        if ctpos >= 0:
#            charset = mime_type[ctpos + 8:]
#        else:
#            charset = None
#
#        content = node.get_content()
#        content = content.read()
##        print content
#
#        msgs =  list(read_po(StringIO(content)))
##        _msgs = []
#        catalog = Catalog(self.env, '', catalog_path, revision, '/trunk')
#        catalog.save()
##        print 555, catalog.__dict__
#        for msg in msgs[1:]:
#            m = Message(self.env, catalog.id, msg.id)
#            m.msgstr = msg.string
#            m.flags = msg.flags
#            m.ac = msg.auto_comments
#            m.uc = msg.user_comments
#            m.previous_id = msg.previous_id
#            m.lineno = msg.lineno
#            m.save()
#            try:
#                m.context = msg.context
#            except AttributeError:
#                pass
#            print 789, msg.locations
#            for fname,lineno in msg.locations:
#                print 7899, fname, lineno
#                location = Location(self.env, m.id, fname, lineno)
#                location.save()
##            _msgs.append(m)
#
##        for msg in _msgs:
##            print 444, msg.locations
##        print _msgs
##        catalog = Catalog(self.env, '', catalog_path, revision)
##        print 444, catalog.messages[-1].__dict__
        return 'l10n_messages.html', {'catalog': catalog}, None
