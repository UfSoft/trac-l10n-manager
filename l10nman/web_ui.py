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
from trac.web.chrome import add_link, add_stylesheet, add_script

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
        match = re.match(r'^/translat(e|ions)(?:/(.*))?', req.path_info)
        if match:
            return True
        return False

    def process_request(self, req):
        add_stylesheet(req, 'l10nman/css/l10n_style.css')
        match = re.match(r'^/(translate|translations)'
                         r'(?:/([0-9]+)?)?(?:/([0-9]+)?)?', req.path_info)
        if match:
            subprocess = match.group(1)
            if subprocess == 'translate':
                msgid = match.group(2)
                return self.process_translate_request(req, msgid)
            elif subprocess == 'translations':
                locale_id = match.group(2)
                page = match.group(3) or 1
                if locale_id:
                    # Render specific locale
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
        add_script(req, 'l10nman/js/dynamic.js')
        show_translated = req.args.get('show_translated', None)
        if not page:
            url = "/%s/1" % locale_id
            req.redirect(req.href.translations(url,
                                               show_translated=show_translated))
        if req.method == 'POST':
            url = "/%s/%s" % (locale_id, page)
            req.redirect(req.href.translations(url,
                                               show_translated=show_translated))

        data = {}
        data['show_translated'] = show_translated
        page = int(page or 1)
        locale = LocaleCatalog.get_by_id(self.env, locale_id)
        data['locale'], data['english_name'], data['display_name'] = \
                                            AVAILABLE_LOCALES[locale.locale]
        data['catalog'] = locale

        messages = show_translated=='on' and locale.messages or \
                                                            locale.untranslated

        paginator = Paginator(messages, page-1, 5)
        data['messages'] = paginator
        shown_pages = paginator.get_shown_pages(30)
        pagedata = []
        for show_page in shown_pages:
            url = "/%s/%s" % (locale_id, show_page)
            page_href = req.href.translations(
                                        url, show_translated=show_translated)
            pagedata.append([page_href, None, str(show_page),
                             'page %s' % show_page])
        fields = ['href', 'class', 'string', 'title']
        paginator.shown_pages = [dict(zip(fields, p)) for p in pagedata]
        paginator.current_page = {'href': None, 'class': 'current',
                                  'string': str(paginator.page + 1),
                                  'title':None}
        if paginator.has_next_page:
            next_href = req.href.translations("/%s/%s" % (locale_id, page+1),
                                              show_translated=show_translated)
            add_link(req, 'next', next_href, _('Next Page'))
        if paginator.has_previous_page:
            prev_href = req.href.translations("/%s/%s" % (locale_id, page-1),
                                              show_translated=show_translated)
            add_link(req, 'prev', prev_href, _('Previous Page'))
        return 'l10n_messages.html', data, None


    def process_translate_request(self, req, msgid):
        pass
