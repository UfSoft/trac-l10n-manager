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
from trac.web.chrome import add_link, add_stylesheet

from trac.mimeview import *
from trac.util.presentation import Paginator
from trac.util.translation import _
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
            print 1234, match.groups()
            return True

    def process_request(self, req):
        add_stylesheet(req, 'l10nman/css/l10n_style.css')
        match = re.match(r'^/translations/([0-9]+)?(?:/([0-9]+)?)?', req.path_info)
        id, page = None, None
        data = {}
        if match:
            id, page = match.groups()

        if id:
            page = int(page or 1)
            catalog = Catalog.get_by_id(self.env, id)
            data['catalog'] = catalog
            paginator = Paginator(catalog.messages, page-1, 5)
            data['messages'] = paginator
            shown_pages = paginator.get_shown_pages(17)
            pagedata = []
            for show_page in shown_pages:
                page_href = req.href.translations("/%s/%s" % (id, show_page))
                pagedata.append([page_href, None, str(show_page), 'page %s' % show_page])
            fields = ['href', 'class', 'string', 'title']
            paginator.shown_pages = [dict(zip(fields, p)) for p in pagedata]
            paginator.current_page = {'href': None, 'class': 'current',
                                    'string': str(paginator.page + 1),
                                    'title':None}
            if paginator.has_next_page:
                next_href = req.href.translations("/%s/%s" % (id, page+1))
                add_link(req, 'next', next_href, _('Next Page'))
            if paginator.has_previous_page:
                prev_href = req.href.translations("/%s/%s" % (id, page-1))
                add_link(req, 'prev', prev_href, _('Previous Page'))
#        data['page_href'] = req.href.translations()
        return 'l10n_messages.html', data, None
