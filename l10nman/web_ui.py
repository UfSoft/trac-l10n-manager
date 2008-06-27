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
from trac.web.chrome import add_link, add_stylesheet, add_script, add_ctxtnav

from trac.mimeview import *
from trac.util.presentation import Paginator
from trac.util.translation import _
from trac.versioncontrol.web_ui.util import *

from babel.messages.pofile import read_po

from l10nman.model import *
from l10nman.utils import AVAILABLE_LOCALES


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
        match = re.match(r'^/(:?re)?translat(e|ions)(?:/(.*))?', req.path_info)
        if match:
            return True
        return False

    def process_request(self, req):
        add_stylesheet(req, 'l10nman/css/l10n_style.css')
        match = re.match(r'^/((re)?translate|translations)'
                         r'(?:/([0-9]+)?)?(?:/([0-9]+)?)?', req.path_info)
        if match:
            print 789999, match.groups()
            subprocess = match.group(1)
            if subprocess == 'translate':
                locale_id = match.group(3)
                msgid = match.group(4)
                return self.process_translate_request(req, locale_id, msgid)
            elif subprocess == 'retranslate':
                locale_id = match.group(3)
                msgid = match.group(4)
                return self.process_retranslate_request(req, locale_id, msgid)
            elif subprocess == 'translations':
                locale_id = match.group(3)
                page = match.group(4) or 1
                if locale_id:
                    # Render specific locale
                    add_ctxtnav(req, tag.a(_('Help To Translate'),
                                           href=req.href.translate(locale_id),
                                           title=_('Help To Translate')))
                    return self.render_locale(req, locale_id, page)
                # Render all locales
                return self.process_locales_request(req, locale_id, page)

    def process_locales_request(self, req, locale_id, page):
        data = {}

        catalogs = LocaleCatalog.get_all(self.env)

        data = {}
        locales_data = []

        for catalog in catalogs:
            locale, english_name, display_name = \
                                            AVAILABLE_LOCALES[catalog.locale]

            stats = catalog.stats
            if stats:
                translated, translated_percent, fuzzy, fuzzy_percent, \
                untranslated, untranslated_percent = stats
            else:
                translated = translated_percent = fuzzy = fuzzy_percent = \
                untranslated = untranslated_percent = 0

            locales_data.append({
                'catalog': catalog,
                'locale': locale,
                'english_name': english_name,
                'display_name': display_name,
                'fuzzy': fuzzy,
                'fuzzy_percent': fuzzy_percent,
                'translated': translated,
                'translated_percent': translated_percent,
                'untranslated': untranslated,
                'untranslated_percent': untranslated_percent
            })
        data['locales'] = locales_data

        return 'l10n_locales_list.html', data, None


    def render_locale(self, req, locale_id, page=1):
        if not page:
            req.redirect(req.href.translations(locale_id, 1))
        if req.method == 'POST':
            req.redirect(req.href.translations(locale_id, page))

        data = {}
        page = int(page or 1)
        locale = LocaleCatalog.get_by_id(self.env, locale_id)
        data['locale'], data['english_name'], data['display_name'] = \
                                            AVAILABLE_LOCALES[locale.locale]
        data['catalog'] = locale

        paginator = Paginator(locale.messages, page-1, 5)
#        print [n[0].flags for n in [t for t in [m.translations(locale_id) for m in paginator] if t]]
        data['messages'] = paginator
        shown_pages = paginator.get_shown_pages(25)
        pagedata = []
        for show_page in shown_pages:
            page_href = req.href.translations(locale_id, show_page)
            pagedata.append([page_href, None, str(show_page),
                             'page %s' % show_page])
        fields = ['href', 'class', 'string', 'title']
        paginator.shown_pages = [dict(zip(fields, p)) for p in pagedata]
        paginator.current_page = {'href': None, 'class': 'current',
                                  'string': str(paginator.page + 1),
                                  'title':None}
        if paginator.has_next_page:
            add_link(req, 'next', req.href.translations(locale_id, page+1),
                     _('Next Page'))
        if paginator.has_previous_page:
            add_link(req, 'prev', req.href.translations(locale_id, page-1),
                     _('Previous Page'))
        return 'l10n_messages.html', data, None


    def process_translate_request(self, req, locale_id, msgid):
        if not msgid:
            # send a random untranslated message
            pass
        pass

    def process_retranslate_request(self, req, locale_id, msgid):
        pass
