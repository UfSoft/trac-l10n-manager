# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et

import posixpath
from cStringIO import StringIO

from trac.core import Component, implements, TracError
from trac.admin.api import IAdminPanelProvider
from trac.resource import ResourceNotFound
from trac.util.translation import _, ngettext
from trac.versioncontrol import NoSuchChangeset
from trac.versioncontrol.web_ui.util import get_existing_node
from trac.web.chrome import add_notice, add_script

from babel.messages.pofile import read_po
from genshi.builder import tag
from tracext.sa import session

from tl10nm.model import *

class L10NAdminCatalogs(Component):
    implements(IAdminPanelProvider)
    env = log = config = None # make pylint happy
    hrefs_cache = {}

    # IAdminPageProvider methods
    def get_admin_panels(self, req):
        if 'L10N_ADMIN' in req.perm:
            yield ('translations', 'L10N Manager', 'catalogs', _('Catalogs'))

    def render_admin_panel(self, req, cat, page, path_info):
        req.perm.require('L10N_ADMIN')

        add_script(req, 'tl10nm/js/autocomplete.js')
        add_script(req, 'tl10nm/js/tl10nm.js')
        add_script(req, 'tl10nm/js/jquery.jTipNG.js')

        data = {}
        if req.method == 'POST':
            if req.args.get('delete_selected'):
                data.update(self.delete_catalogs(req))
            elif req.args.get('add_catalog'):
                data.update(self.add_catalog(req))

        Session = session(self.env)

        repos = self.env.get_repository(req.authname)
        data['youngest_rev'] = repos.short_rev(repos.youngest_rev)
        data['projects'] = Session.query(Project).all()

        return 'l10n_admin_catalogs.html', data

    def add_catalog(self, req):
        data = {}
        errors = []
        data['fpath'] = fpath = req.args.get('fpath')
        data['project_id'] = project_id = req.args.get('project_id')

        def add_error(error):
            errors.append(error)
            data['error'] = tag.ul(*[tag.li(e) for e in errors])
            return data

        if not project_id:
            return add_error(_("You must first create a project"))

        if not fpath or fpath == '/':
            return add_error(_("You must define the catalog path"))

        repos = self.env.get_repository(req.authname)
        revision = repos.youngest_rev
        try:
            node = get_existing_node(req, repos, fpath, revision)
        except NoSuchChangeset, e:
            raise ResourceNotFound(e.message, _('Invalid Changeset Number'))

        Session = session(self.env)

        catalog = Session.query(Catalog).get_by(fpath=fpath)
        if catalog:
            return add_error(_("Catalog already exists"))

        project = Session.query(Project).get(int(project_id))
        description = req.args.get('description', '')

        catalog = Catalog(project, fpath, description,
                          repos.short_rev(node.rev))

        messages = list(read_po(StringIO(node.get_content().read())))

        for msg in messages[1:]:
            if msg.pluralizable:
                string, plural = msg.id
            else:
                string = msg.id
                plural = ''
            try:
                context = msg.context
            except AttributeError:
                context = ''

            message = MsgID(catalog, string, plural, context)
            catalog.messages.append(message)

            for comment in msg.auto_comments:
                message.comments.append(MsgIDComment(message, comment))

            for flag in msg.flags:
                message.flags.append(MsgIDFlag(message, flag))

            for fname, lineno in msg.locations:
                href = self._get_location_href(req, fpath, fname, lineno)
                location = MsgIDLocation(message, fname, lineno, href)
                message.locations.append(location)

        project.catalogs.append(catalog)
        Session.commit()

        return data

    def delete_catalogs(self, req):
        selected = req.args.getlist('sel')
        Session = session(self.env)
        for catalog in selected:
            Session.delete(Session.query(Catalog).get(int(catalog)))
        add_notice(req, ngettext("Catalog deleted.", "Catalogs deleted.",
                                 len(selected)))
        Session.commit()
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
            return href(self.hrefs_cache.get(fname)) + "#L%d" % lineno
        else:
            return ''
