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
from trac.versioncontrol import NoSuchChangeset, NoSuchNode
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

        if req.get_header('X-Requested-With'):
            # AJAX request
            print 'AJAX', req.args
            if req.args.get('locale'):
                self._return_locales_list(req)
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

        catalogs = CatalogTemplate.get_all(self.env)
        data['catalogs'] = catalogs
        repos = self.env.get_repository(req.authname)
        data['youngest_rev'] = repos.short_rev(repos.youngest_rev)
        return 'l10n_admin_catalogs.html', data

    def _delete_catalogs(self, req):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        selected = req.args.getlist('sel')
        for sel in selected:
            catalog = CatalogTemplate(self.env, sel)
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
            errors.append(error)
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


        template = CatalogTemplate(self.env, fpath) #, node.rev)
        if template.revision:
            add_error("Catalog already exists")
        else:
            template.revision = repos.short_rev(node.rev)
            template.save()

        messages = list(read_po(StringIO(node.get_content().read())))
        for msg in messages[1:]:
            if msg.pluralizable:
                m = Message(self.env, template.fpath, msg.id[0])
                m.plural = msg.id[1]
            else:
                m = Message(self.env, template.fpath, msg.id)
            m.msgstr = msg.string
            m.flags = msg.flags
            m.ac = msg.auto_comments
#            m.uc = msg.user_comments
            m.previous_id = msg.previous_id
            m.lineno = msg.lineno
            m.save()
            try:
                m.context = msg.context
            except AttributeError:
                pass
            for fname,lineno in msg.locations:
                location = Location(self.env, m.id, fname, lineno)
                location.href = self._get_location_href(req, fpath,
                                                        fname, lineno)
                location.save()
        add_notice(req, "Catalog added.")
        return data

    def handle_locales(self, req):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        data = {}
        if req.method == 'POST':
            if req.args.get('delete_selected'):
                data.update(self._delete_locale(req))
            elif req.args.get('add_locale'):
                data.update(self._add_locale(req))

        templates = CatalogTemplate.get_all(self.env)
        data['catalog_templates'] = templates
        locales = LocaleCatalog.get_all(self.env)
        data['locales'] = locales
        repos = self.env.get_repository(req.authname)
        data['youngest_rev'] = repos.short_rev(repos.youngest_rev)
        return 'l10n_admin_locales.html', data


    def _add_locale(self, req):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        data = {}
        errors = []
        catalog_template = req.args.get('catalog_template', None)
        locale = req.args.get('locale')
        locale_catalog_path = req.args.get('catalog')
        def add_error(error):
            errors.append(error)
            data['error'] = tag.ul(*[tag.li(e) for e in errors])
            data['locale'] = locale
            data['catalog'] = locale_catalog_path
            return data

        if not catalog_template:
            return add_error("You must first create a catalog template")
        catalog_template = CatalogTemplate(self.env, catalog_template)
        if not locale:
            return add_error("You must define the new catalog's locale")

        if locale_catalog_path:
            repos = self.env.get_repository(req.authname)
            revision = repos.youngest_rev
            try:
                node = get_existing_node(req, repos, locale_catalog_path, revision)
            except NoSuchChangeset, e:
                raise ResourceNotFound(e.message, _('Invalid Changeset Number'))

        if not node.kind == 'file':
            raise TracError('Unknown Catalog')

        locale_catalog = LocaleCatalog(self.env, locale, locale_catalog_path,
                                       repos.short_rev(node.rev),
                                       catalog_template.fpath)
        if locale_catalog.id:
            return add_error("Catalog already exists")
        locale_catalog.save()

        messages = list(read_po(StringIO(node.get_content().read())))
        for msg in messages[1:]:
            if isinstance(msg.string, basestring):
                msgid = msg.id
                msgstrs = [msg.string]
            else:
                msgid = msg.id[0]
                msgstrs = msg.string

            m = Message(self.env, catalog_template.fpath, msgid)
            for idx, string in enumerate(msgstrs):
                if string:
                    t = Translation(self.env, locale_catalog.id, m.id,
                                    string, idx, req.authname)
                    t.flags = msg.flags
                    t.uc = msg.user_comments
                    t.status = 'reviewed'
                    t.save()
        self.log.debug("Updating catalog statistics")
        locale_catalog.update_stats()

        add_notice(req, "Locale added.")
        return data

    def _delete_locale(self, req):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        selected = req.args.getlist('sel')
        print 987, selected
        for id in selected:
            catalog = LocaleCatalog.get_by_id(self.env, id)
            if catalog:
                catalog.delete()

        add_notice(req, "Catalog(s) deleted.")

        return {}

    def _return_repo_paths_list(self, req):
        repopath = req.args.get('q')
        if not repopath.startswith('/'):
            repopath = '/%s' % repopath

        repos = self.env.get_repository(req.authname)

        def get_node_entries(path):
            # Should probably try to cache these searches,
            # although only meant for admins
            if not path.startswith('/'):
                path = '/%s' % path
            fallback = posixpath.dirname(path)
            try:
                node = repos.get_node(str(path), repos.youngest_rev)
            except (TracError, NoSuchNode):
                node = repos.get_node(fallback, repos.youngest_rev)
            node_entries = list(node.get_entries())
            entries = []
            for entry in node_entries:
                path = entry.path
                if not path.startswith('/'):
                    path = '/%s' % path
                if path.startswith(repopath):
                    # Only return those that we're interested in
                    entries.append(entry)
            entries.sort(key=attrgetter('path'))
            return entries

        entries = get_node_entries(repopath)

        if not entries:
            req.write(tag.center(tag.em("No matches found on repository for ",
                                        tag.b(repopath))))
            raise RequestDone

        while len(entries) <= 1:
            # If returning only one entry, return a file no matter how deep
            if entries[0].kind == 'dir':
                entries = get_node_entries(entries[0].path)
            elif entries[0].kind == 'file':
                break

        req.write('<ul>')
        for entry in entries:
            path = entry.path
            if not path.startswith('/'):
                path = '/%s' % path
            req.write(tag.li(tag.b(repopath), tag(path.split(repopath)[1])))
        req.write('</ul>')
        raise RequestDone

    def _return_locales_list(self, req):
        query = req.args.get('locale')
        if not query:
            req.write(tag.center(tag.em('No matches')))
            raise RequestDone

        matches = [AVAILABLE_LOCALES[l]
                   for l in AVAILABLE_LOCALES.keys() if
                   l.lower().startswith(query.lower())]

        if not matches:
            req.write(tag.center(tag.em("No matches found for locale ",
                                        tag.b(query))))
            raise RequestDone
        req.write('<ul>')
        for loc, eng_name, disp_name in matches:
            req.write(tag.li(tag.b(loc), tag.br,
                             tag.em(disp_name), tag.br, tag.em(eng_name),
                             realvalue=loc))
        req.write('</ul>')
        raise RequestDone




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
            return href(self.hrefs_cache.get(fname)) + "#L%d" % lineno
        else:
            return ''
