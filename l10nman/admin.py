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

import posixpath

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
from l10nman.utils import AVAILABLE_LOCALES

class L10NAdminModule(Component):
    hrefs_cache = {}
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

        catalogs = Catalog.get_all(self.env, locale='')
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
            elif req.args.get('add_locale'):
                data.update(self._add_locale(req))

        catalogs = Catalog.get_all(self.env, locale='')
        data['catalog_templates'] = catalogs
        locales = Catalog.get_all(self.env, no_empty_locale=True)
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
                req.write(tag.li(path))
        req.write('</ul>')
        raise RequestDone

    def _return_locales_list(self, req):
        query = req.args.get('locale')
        if not query:
            raise RequestDone

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
        for sel in selected:
            catalog = Catalog.get_by_id(self.env, sel)
            if catalog:
                catalog.delete()
                add_notice(req, "Catalog(s) deleted.")
        return {}

    def _add_catalog(self, req):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        data = {}
        errors = []
        fpath = req.args.get('fpath')
        def add_error(error):
            errors.append()
            data['error'] = tag.ul(*[tag.li(e) for e in errors])
            data['fpath'] = fpath
            return data

        if not fpath or fpath == '/':
            add_error("You must define the catalog path")

        repos = self.env.get_repository(req.authname)
        revision = repos.youngest_rev
        try:
            node = get_existing_node(req, repos, fpath, revision)
        except NoSuchChangeset, e:
            raise ResourceNotFound(e.message, _('Invalid Changeset Number'))

        locale = req.args.get('locale', '')
        catalog = Catalog(self.env, locale, fpath, node.rev)
        if catalog.id:
            add_error("Catalog already exists")
        else:
            catalog.save()

        messages = list(read_po(StringIO(node.get_content().read())))
        for msg in messages[1:]:
            if msg.pluralizable:
                m = Message(self.env, catalog.id, msg.id[0])
                m.plural = msg.id[1]
            else:
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
            for fname,lineno in msg.locations:
                location = Location(self.env, m.id, fname, lineno)
                location.href = self._get_location_href(req, fpath, fname, lineno)
                location.save()
        add_notice(req, "Catalog added.")
        return data

    def _add_locale(self, req):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        data = {}
        errors = []
        template_id = req.args.get('catalog_template', None)
        if not template_id:
            errors.append("You must first create a catalog template")
        catalog_template = Catalog.get_by_id(self.env, req.args.get('catalog_template'))
        locale = req.args.get('locale')
        if not locale:
            errors.append("You must define the new catalog's locale")

        catalog_path = req.args.get('catalog')
        if catalog_path:
            repos = self.env.get_repository(req.authname)
            revision = repos.youngest_rev
            try:
                node = get_existing_node(req, repos, catalog_path, revision)
            except NoSuchChangeset, e:
                raise ResourceNotFound(e.message, _('Invalid Changeset Number'))

        catalog = Catalog(self.env, locale, catalog_template.repobase,
                          catalog_path, node.rev)
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
            for fname,lineno in msg.locations:
                location = Location(self.env, m.id, fname, lineno)
                location.save()

        if errors:
            data['error'] = tag.ul(*[tag.li(e) for e in errors])
            data['repobase'] = repobase
            data['fpath'] = fpath
        add_notice(req, "Catalog added.")
        return data

    def _delete_locale(self, req):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        selected = req.args.getlist('sel')
        print 987, selected
        for id in selected:
            catalog = Catalog.get_by_id(self.env, id)
#            cursor.execute("SELECT locale, repobase, fpath, revision "
#                           "FROM l10n_catalogs WHERE id=%s", (sel,))
#            row = cursor.fetchone()
#            if row:
#                catalog = Catalog(self.env, *row)
            if catalog:
                catalog.delete()

        add_notice(req, "Catalog(s) deleted.")

        return {}

    def _get_location_href(self, req, catalog_path, fname, lineno):
        catalog_path_parts = catalog_path.replace('\\', '/').split('/')
        href = req.href.browser

        repos = self.env.get_repository(req.authname)
        revision = repos.youngest_rev

        fname = fname.replace('\\', '/')
        path = ''
        for part in catalog_path_parts:
            path = posixpath.join(path, part)
            if fname not in self.hrefs_cache:
                try:
                    repos.get_node(posixpath.join(path, fname), revision)
                    self.hrefs_cache[fname] = posixpath.join(path, fname)
                except TracError:
                    self.hrefs_cache[fname] = False
        if self.hrefs_cache.get(fname) is not False:
            print href(self.hrefs_cache.get(fname)) + "#L%d" % lineno
            return href(self.hrefs_cache.get(fname)) + "#L%d" % lineno
        else:
            return ''
