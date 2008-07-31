# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et

import re
from cStringIO import StringIO

from trac.core import Component, implements, TracError
from trac.admin.api import IAdminPanelProvider
from trac.perm import PermissionSystem
from trac.resource import ResourceNotFound
from trac.util.translation import _, ngettext
from trac.versioncontrol import NoSuchChangeset
from trac.versioncontrol.web_ui.util import get_existing_node
from trac.web.chrome import add_notice, add_script

from babel.messages.pofile import read_po
from babel.messages.plurals import get_plural

from genshi.builder import tag
from tracext.sa import session

from tl10nm.model import *

class L10NAdminLocales(Component):
    implements(IAdminPanelProvider)
    env = log = config = None # make pylint happy

    # IAdminPageProvider methods
    def get_admin_panels(self, req):
        if 'L10N_MODERATE' in req.perm:
            # Is user a manager of any locale
            Session = session(self.env)
            if Session.query(LocaleAdmin).filter_by(sid=req.authname).first():
                yield ('translations', 'L10N Manager', 'locales', _('Locales'))

    def render_admin_panel(self, req, cat, page, path_info):
        req.perm.require('L10N_MODERATE')

        add_script(req, 'tl10nm/js/autocomplete.js')
        add_script(req, 'tl10nm/js/tl10nm.js')
        add_script(req, 'tl10nm/js/jquery.jTipNG.js')
        add_script(req, 'tl10nm/js/jquery.tablescroller.js')
        # add_stylesheet(req, 'tl10nm/css/l10n_style.css')
        # Needs to be on the template so that trac's admin.css get's overridden
        match = re.match(r'^/admin/translations/locales/'
                         r'(admins|downloads)/([\d]+)(?:/(.*))?', req.path_info)
        if match:
            action, locale_id, fname = match.groups()
            if action == 'admins':
                return self.handle_edit_locale_admins(req, locale_id)
            elif action == 'downloads':
                return self.handle_downloads(req, locale_id, fname)
        return self.handle_locales(req, path_info)

    def handle_locales(self, req, path_info):
        data = {}

        if req.method == 'POST':
            if req.args.get('delete_selected'):
                data.update(self.delete_locale(req))
            elif req.args.get('add_locale'):
                data.update(self.add_locale(req))

        Session = session(self.env)
        data['known_users'] = self.env.get_known_users()
        data['projects'] = projects = Session.query(Project).all()

        repos = self.env.get_repository(req.authname)
        data['youngest_rev'] = repos.short_rev(repos.youngest_rev)
        return 'l10n_admin_locales.html', data

    def add_locale(self, req):
        data = {}
        errors = []
        catalog_template_id = req.args.get('catalog_template', None)
        locale = req.args.get('locale')
        locale_admins = req.args.getlist('admins')

        def add_error(error):
            errors.append(error)
            data['error'] = tag.ul(*[tag.li(e) for e in errors if e])
            data['locale'] = locale
            return data

        if not catalog_template_id:
            errors.append(_("You must first create a catalog template"))

        if not locale:
            return add_error(_("You must define the new catalog's locale"))
        if not locale_admins:
            return add_error(_("You must define at least one locale admin"))

        Session = session(self.env)
        catalog = Session.query(Catalog).get(catalog_template_id)

        num_plurals = get_plural(locale=locale).num_plurals

        _locale = Session.query(Locale).filter_by(locale=locale,
                                                  catalog_id=catalog.id).first()
        if _locale:
            data['locale'] = _locale
            return add_error(_("Locale Exists Already"))

        locale = Locale(catalog, locale, num_plurals)
        for sid in locale_admins:
            locale.admins.append(LocaleAdmin(locale, sid))

        catalog.locales.append(locale)

        Session.commit()

        perm = PermissionSystem(self.env)
        sids_without_necessary_perms = []
        for admin in locale.admins:
            if not 'L10N_MODERATE' in perm.get_user_permissions(admin.sid):
                sids_without_necessary_perms.append(admin.sid)

        if sids_without_necessary_perms:
            msg = ngettext(
                "%s does not have the required permissions to administrate." % \
                ', '.join(["'%s'" % s for s in sids_without_necessary_perms]),
                "%s don't have the required permissions to administrate." % \
                ', '.join(["'%s'" % s for s in sids_without_necessary_perms]),
                 len(sids_without_necessary_perms))
            add_error(tag(msg, _(" Don't forget to "),
                          tag.a(_('update permissions'),
                                href=req.href.admin('general', 'perm')),
                          '.'))

        add_notice(req, _("Locale added."))

        # Are we importing existing data
        locale_catalog_path = req.args.get('catalog')
        include_fuzzy = req.args.get('include_fuzzy') == '1'

        if not locale_catalog_path or locale_catalog_path == '/':
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

    def handle_downloads(self, req, locale_id, fname):
        locale = session(self.env).query(Locale).get(int(locale_id))
        if not locale:
            raise TracError(_("Unknown locale id: %s") % locale_id)

        self.log.debug("User '%s' is requesting '%s' download for locale '%s'",
                       req.authname, fname, locale.locale)

        if fname.endswith('.po'):
            tmpfile = locale.get_pofile()
            req.send_file(tmpfile[1], mimetype='text/x-gettext')
        elif fname.endswith('.mo'):
            tmpfile = locale.get_mofile()
            req.send_file(tmpfile[1], mimetype='application/x-gettext')
        else:
            raise TracError(_('Unknown download'))

    def handle_edit_locale_admins(self, req, locale_id):
        if not locale_id:
            req.redirect(req.href.admin('translations', 'locales'))

        Session = session(self.env)
        locale = Session.query(Locale).get(int(locale_id))
        known_users = self.env.get_known_users()
        errors = []
        perm = PermissionSystem(self.env)
        sids_without_necessary_perms = []
        for admin in locale.admins:
            if not 'L10N_MODERATE' in perm.get_user_permissions(admin.sid):
                sids_without_necessary_perms.append(admin.sid)

        if sids_without_necessary_perms:
            msg = ngettext(
                "%s does not have the required permissions to administrate." % \
                ', '.join(["'%s'" % s for s in sids_without_necessary_perms]),
                "%s don't have the required permissions to administrate." % \
                ', '.join(["'%s'" % s for s in sids_without_necessary_perms]),
                 len(sids_without_necessary_perms))
            errors.append(
                tag(msg, _(" Don't forget to "),
                    tag.a(_('update permissions'),
                          href=req.href.admin('general', 'perm')), '.'))

        if req.method == 'POST' and len(req.args.getlist('admins')) >= 1:
            current_admins = req.args.getlist('current_admins')
            selected = req.args.getlist('admins')

            self.log.debug('Current Admins: %s', current_admins)
            self.log.debug('Selected Admins: %s', selected)

            allow_delete_admins = len(selected) >= 1
            if not allow_delete_admins:
                errors.append(
                    tag(_("There must be at least on admin for each locale.")))

            for admin in current_admins:
                if not allow_delete_admins:
                    break
                if admin not in selected:
                    locale_admin = Session.query(LocaleAdmin). \
                        filter(locale_admin_table.c.sid==admin).first()
                    Session.delete(locale_admin)
            for admin in selected:
                if admin not in locale.admins:
                    locale.admins.append(LocaleAdmin(locale, admin))
            Session.commit()
            req.redirect(req.href.admin('translations', 'locales'))
        elif req.method == 'POST' and len(req.args.getlist('admins')) < 1:
            errors.append(
                tag(_("There must be at least on admin for each locale.")))

        data = {'locale': locale, 'known_users': known_users}
        if errors:
            data['error'] = tag.ul(*[tag.li(e) for e in errors if e])

        return 'l10n_admin_locale_admins.html', data
