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

from cStringIO import StringIO
from operator import attrgetter

from trac.core import *
from trac.admin.api import IAdminPanelProvider
from trac.web.chrome import add_script, add_stylesheet


from trac.resource import ResourceNotFound
from trac.util.translation import _
from trac.versioncontrol import NoSuchChangeset
from trac.versioncontrol.web_ui.util import get_existing_node
from trac.web.main import RequestDone
from trac.web.chrome import add_warning, add_notice


from genshi.builder import tag
from babel import localedata
from babel.core import Locale
from babel.messages.pofile import read_po


from l10nman.model import *

AVAILABLE_LOCALES = {}

class L10NAdminModule(Component):
    implements(IAdminPanelProvider)

    # IAdminPageProvider methods
    def get_admin_panels(self, req):
        yield ('translations', 'L10N Manager', 'catalogs', 'Catalog Templates')
        yield ('translations', 'L10N Manager', 'locales', 'Locales')

    def render_admin_panel(self, req, cat, page, path_info):
        add_script(req, 'l10nman/js/autocomplete.js')
        add_stylesheet(req, 'l10nman/css/l10n_style.css')

        if req.get_header('X-Requested-With'):
            # AJAX request
            print 'AJAX', req.args
            if req.args.get('locale'):
                self._return_locales_list(req)
            elif req.args.get('repobase'):
                self._return_repo_paths_list(req, dirs_only=True)
            else:
                self._return_repo_paths_list(req)

        if page == 'catalogs':
            return self.handle_catalogs(req)
        elif page == 'locales':
            return self.handle_locales(req)

    def handle_catalogs(self, req):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        data = {}
        if req.method == 'POST':
            if req.args.get('delete_selected'):
                data.update(self._delete_catalogs(req))
            elif req.args.get('add_catalog'):
                data.update(self._add_catalog(req))

        cursor.execute("SELECT fpath, repobase, revision FROM "
                       "l10n_catalogs WHERE locale=''")
        rows = cursor.fetchall()
        catalogs = []
        for row in rows:
            cat = Catalog(self.env, '', *row)
            catalogs.append(cat)
        print catalogs
        data['catalogs'] = catalogs
        data['youngest_rev'] = self.env.get_repository(req.authname).youngest_rev
        return 'l10n_admin_catalogs.html', data

    def handle_locales(self, req):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        data = {}
        if req.method == 'POST':
            if req.args.get('delete_selected'):
                data.update(self._delete_locale(req))
            elif req.args.get('add_catalog'):
                data.update(self._add_locale(req))

        cursor.execute("SELECT fpath FROM l10n_catalogs WHERE locale=''")
        catalogs = cursor.fetchall()
        data['catalogs'] = catalogs
        cursor.execute("SELECT fpath FROM l10n_catalogs WHERE locale!=''")
        locales = cursor.fetchall()
        data['locales'] = locales
        data['youngest_rev'] = self.env.get_repository(req.authname).youngest_rev
        return 'l10n_admin_locales.html', data

    def _return_repo_paths_list(self, req, dirs_only=False):
        if dirs_only:
            repopath = req.args.get('repobase', '/')
        else:
            repopath = req.args.get('q', '/')

        repos = self.env.get_repository(req.authname)

        try:
            node = get_existing_node(req, repos, repopath, repos.youngest_rev)
        except NoSuchChangeset, e:
            raise ResourceNotFound(e.message, _('Invalid Changeset Number'))

        entries = []
        node_entries = list(node.get_entries())
        node_entries.sort(key=attrgetter('path'))
        req.write('<ul>')
        for entry in node_entries:
            path = entry.path
            if not path.startswith('/'):
                path = '/%s' % path
            if entry.kind == 'dir':
                path = tag.em(path)
            if entry.kind == 'dir':
                req.write(tag.li(path))
            elif not dirs_only:
                req.write.append(tag.li(path))
        req.write('</ul>')
        raise RequestDone

    def _return_locales_list(self, req):
        query = req.args.get('locale')
        if not query:
            raise RequestDone

        if not AVAILABLE_LOCALES:
            self.log.debug("Building Locales Mapping")
            locales = map(Locale.parse, localedata.list())
            for locale in locales:
                if str(locale) not in AVAILABLE_LOCALES:
                    AVAILABLE_LOCALES[str(locale)] = (
                        str(locale), locale.english_name, locale.display_name)

        matches = [AVAILABLE_LOCALES[l]
                   for l in AVAILABLE_LOCALES.keys() if l.startswith(query)]

        req.write('<ul>')
        for loc, eng_name, disp_name in matches:
            req.write(tag.li(tag.b(loc), tag.br,
                             tag.em(disp_name), tag.br, tag.em(eng_name),
                             realvalue=loc))
        req.write('</ul>')
        raise RequestDone

    def _delete_catalogs(self, req):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        selected = req.args.getlist('sel')
        print 987, selected
        for sel in selected:
            cursor.execute("SELECT locale, fpath, repobase, revision "
                           "FROM l10n_catalogs WHERE id=%s", (sel,))
            row = cursor.fetchone()
            if row:
                catalog = Catalog(self.env, *row)
                catalog.delete()

        add_notice(req, "Catalog(s) deleted.")

        return {}

    def _add_catalog(self, req):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        data = {}
        errors = []
        repobase = req.args.get('repobase', None)
        if not repobase:
            errors.append("You must define the Repository Base")
        fpath = req.args.get('fpath')
        if not fpath or fpath == '/':
            errors.append("You must define the catalog path")

        repos = self.env.get_repository(req.authname)
        revision = repos.youngest_rev
        try:
            node = get_existing_node(req, repos, fpath, revision)
        except NoSuchChangeset, e:
            raise ResourceNotFound(e.message, _('Invalid Changeset Number'))

        locale = req.args.get('locale', '')
        catalog = Catalog(self.env, locale, fpath, repobase, node.rev)
        if catalog.id:
            errors.append("Catalog already exists")
        else:
            catalog.save()

        messages = list(read_po(StringIO(node.get_content().read())))
        for msg in messages[1:]:
            m = Message(self.env, catalog.id, msg.id)
            m.msgstr = msg.string
            m.flags = msg.flags
            m.ac = msg.auto_comments
            m.uc = msg.user_comments
            m.previous_id = msg.previous_id
            m.lineno = msg.lineno
            m.save()
            try:
                m.context = msg.context
            except AttributeError:
                pass
            print 789, msg.locations
            for fname,lineno in msg.locations:
                print 7899, fname, lineno
                location = Location(self.env, m.id, fname, lineno)
                location.save()

        if errors:
            data['error'] = tag.ul(*[tag.li(e) for e in errors])
            data['repobase'] = repobase
            data['fpath'] = fpath
        add_notice(req, "Catalog added.")
        return data

    def _add_locale(self, req):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        data = {}
        errors = []
        repobase = req.args.get('repobase', None)
        if not repobase:
            errors.append("You must define the Repository Base")
        fpath = req.args.get('fpath')
        if not fpath or fpath == '/':
            errors.append("You must define the catalog path")

        repos = self.env.get_repository(req.authname)
        revision = repos.youngest_rev
        try:
            node = get_existing_node(req, repos, fpath, revision)
        except NoSuchChangeset, e:
            raise ResourceNotFound(e.message, _('Invalid Changeset Number'))

        locale = req.args.get('locale', '')
        catalog = Catalog(self.env, locale, fpath, repobase, node.rev)
        if catalog.id:
            errors.append("Catalog already exists")
        else:
            catalog.save()

        messages = list(read_po(StringIO(node.get_content().read())))
        for msg in messages[1:]:
            m = Message(self.env, catalog.id, msg.id)
            m.msgstr = msg.string
            m.flags = msg.flags
            m.ac = msg.auto_comments
            m.uc = msg.user_comments
            m.previous_id = msg.previous_id
            m.lineno = msg.lineno
            m.save()
            try:
                m.context = msg.context
            except AttributeError:
                pass
            print 789, msg.locations
            for fname,lineno in msg.locations:
                print 7899, fname, lineno
                location = Location(self.env, m.id, fname, lineno)
                location.save()

        if errors:
            data['error'] = tag.ul(*[tag.li(e) for e in errors])
            data['repobase'] = repobase
            data['fpath'] = fpath
        add_notice(req, "Catalog added.")
        return data
