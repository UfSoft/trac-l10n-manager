# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8

import posixpath
from cStringIO import StringIO
from operator import attrgetter

from trac.admin.api import IAdminPanelProvider
from trac.core import *
from trac.resource import ResourceNotFound
from trac.util.translation import _, ngettext
from trac.versioncontrol import NoSuchChangeset, NoSuchNode
from trac.versioncontrol.web_ui.util import get_existing_node
from trac.web.main import RequestDone
from trac.web.chrome import add_warning, add_notice, add_script, add_stylesheet

from genshi.builder import tag
from babel import localedata
from babel.core import Locale as BabelLocale
from babel.messages.pofile import read_po
from babel.messages.plurals import get_plural

from tl10nm.utils import AVAILABLE_LOCALES
from tl10nm.model import *


class L10NAdminModule(Component):
    implements(IAdminPanelProvider)
    hrefs_cache = {}

    # IAdminPageProvider methods
    def get_admin_panels(self, req):
        if 'L10N_ADMIN' in req.perm:
            yield ('translations', 'L10N Manager', 'catalogs', _('Catalogs'))
            yield ('translations', 'L10N Manager', 'locales', _('Locales'))

    def render_admin_panel(self, req, cat, page, path_info):
        req.perm.require('L10N_ADMIN')
        add_script(req, 'tl10nm/js/autocomplete.js')

        if req.get_header('X-Requested-With'):
            # AJAX request
            self.log.debug('Got an AJAX Request: %r', req.args)
            if req.args.get('locale'):
                self._return_locales_list(req)
            else:
                self._return_repo_paths_list(req)

        if page == 'catalogs':
            return self.handle_catalogs(req)
        elif page == 'locales':
            return self.handle_locales(req)

    # Internal/Custom methods
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
            req.write(tag.center(tag.em(_("No matches found on repository for "),
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
            req.write(tag.center(tag.em(_('No matches'))))
            raise RequestDone

        matches = [AVAILABLE_LOCALES[l]
                   for l in AVAILABLE_LOCALES.keys() if
                   l.lower().startswith(query.lower())]

        if not matches:
            req.write(tag.center(tag.em(_("No matches found for locale "),
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

    # Handle Catalogs
    def handle_catalogs(self, req):
        data = {}
        if req.method == 'POST':
            if req.args.get('delete_selected'):
                data.update(self.delete_catalogs(req))
            elif req.args.get('add_catalog'):
                data.update(self.add_catalog(req))

        catalogs = session(self.env).query(Catalog).all()
        data['catalogs'] = catalogs
        repos = self.env.get_repository(req.authname)
        data['youngest_rev'] = repos.short_rev(repos.youngest_rev)
        return 'l10n_admin_catalogs.html', data

    def add_catalog(self, req):
        data = {}
        errors = []
        fpath = req.args.get('fpath')
        def add_error(error):
            errors.append(error)
            data['error'] = tag.ul(*[tag.li(e) for e in errors])
            data['fpath'] = fpath
            return data

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

        description = req.args.get('description', '')

        catalog = Catalog(fpath, description, repos.short_rev(node.rev))

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

        Session.save(catalog)
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

    # Handle Locales
    def handle_locales(self, req):
        data = {}
        if req.method == 'POST':
            if req.args.get('delete_selected'):
                data.update(self.delete_locale(req))
            elif req.args.get('add_locale'):
                data.update(self.add_locale(req))


        templates = session(self.env).query(Catalog).all()
        data['catalog_templates'] = templates
        locales = session(self.env).query(Locale).options(eagerload('catalog'))
        data['locales'] = locales.all()
        repos = self.env.get_repository(req.authname)
        data['youngest_rev'] = repos.short_rev(repos.youngest_rev)
        return 'l10n_admin_locales.html', data

    def add_locale(self, req):
        data = {}
        errors = []
        catalog_template_id = req.args.get('catalog_template', None)
        locale = req.args.get('locale')

        def add_error(error):
            errors.append(error)
            data['error'] = tag.ul(*[tag.li(e) for e in errors if e])
            data['locale'] = locale
            return data

        if not catalog_template_id:
            errors.append(_("You must first create a catalog template"))

        if not locale:
            return add_error(_("You must define the new catalog's locale"))

        Session = session(self.env)
        catalog = Session.query(Catalog).get(catalog_template_id)

        num_plurals = get_plural(locale=locale).num_plurals

        _locale = Session.query(Locale).filter_by(locale=locale,
                                                  catalog_id=catalog.id).first()
        if _locale:
            data['locale'] = _locale
            return add_error(_("Locale Exists Already"))

        locale = Locale(catalog, locale, num_plurals)
        catalog.locales.append(locale)

        Session.commit()

        add_notice(req, _("Locale added."))

        # Are we importing existing data
        locale_catalog_path = req.args.get('catalog')
        include_fuzzy = req.args.get('include_fuzzy') == '1'

        if not locale_catalog_path:
            return data

        repos = self.env.get_repository(req.authname)
        revision = repos.youngest_rev
        try:
            node = get_existing_node(req, repos, locale_catalog_path, revision)
        except NoSuchChangeset, e:
            raise ResourceNotFound(e.message, _('Invalid Changeset Number'))

        if not node.kind == 'file':
            raise TracError(_('Unknown Catalog'))

        messages = list(read_po(StringIO(node.get_content().read()),
                                locale=locale))
        for msg in messages[1:]:
            should_break = False
            if 'fuzzy' in msg.flags and not include_fuzzy:
                should_break = True
            elif isinstance(msg.id, (list, tuple)):
                if len([s for s in list(msg.string) if s]) != len(msg.string):
                    # if any of the plurals is empty, don't add the translation
                    # we don't want incomplete translations
                    should_break = True
                string, plural = msg.id
                strings = msg.string
            else:
                if not msg.string:
                    # If we don't have a translation, continue to next one
                    should_break = True
                string, plural = msg.id, ''
                strings = [msg.string]


            if should_break:
                continue # Let's go to the next message

            msgid = Session.query(MsgID).filter_by(string=string,
                                                   plural=plural).first()

            if not msgid:
                add_error(_("Unknown msgid. Is this the right localized "
                            "catalog for this template? Aborting data import."))

            if not plural:
                strings = [msg.string]
            else:
                strings = msg.string

            translation = Translation(locale, msgid, req.authname,
                                      fuzzy='fuzzy' in msg.flags)
            for comment in msg.user_comments:
                translation.comments.append(TranslationComment(translation,
                                                               comment))
            translation.comments.append(
                TranslationComment(translation,
                                   "Imported from repository catalog"))

            for index, string in enumerate(strings):
                if string:
                    translation.strings.append(TranslationString(translation,
                                                                 string, index))

            locale.translations.append(translation)
        Session.commit()

        add_notice(req, _("Data Imported."))
        return data

    def delete_locale(self, req):
        selected = req.args.getlist('sel')
        Session = session(self.env)
        for id in selected:
            Session.delete(Session.query(Locale).get(int(id)))
        Session.commit()
        add_notice(req, ngettext("Locale deleted.", "Locales deleted.",
                                 len(selected)))
        return {}

