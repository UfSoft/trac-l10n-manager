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
from babel.messages.pofile import read_po

from l10nman.model import *

class L10NAdminModule(Component):
    implements(IAdminPanelProvider)

    # IAdminPageProvider methods
    def get_admin_panels(self, req):
        yield ('translations', 'L10N Manager', 'catalogs', 'Manage Catalogs')

    def render_admin_panel(self, req, cat, page, path_info):
        add_script(req, 'common/js/suggest.js')
        add_stylesheet(req, 'l10nman/l10n_style.css')

        if req.get_header('X-Requested-With'):
            # AJAX request
            self._return_repo_paths_list(req)

        if page == 'catalogs':
            return self.handle_catalogs(req)

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
        print 123, data
        return 'l10n_admin_locales.html', data

    def _return_repo_paths_list(self, req):
        repopath = req.args.get('q', '/')

        repos = self.env.get_repository(req.authname)

        try:
            node = get_existing_node(req, repos, repopath, repos.youngest_rev)
        except NoSuchChangeset, e:
            raise ResourceNotFound(e.message, _('Invalid Changeset Number'))

        entries = []
        for entry in node.get_entries():
            path = entry.path
            if not path.startswith('/'):
                path = '/%s' % path
            if entry.kind == 'dir':
                path = tag.b(path)
            entries.append(tag.li(path))
        req.write(tag.ul(*entries))
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

        locale = ''
        catalog = Catalog(self.env, locale, fpath, repobase, revision)
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
