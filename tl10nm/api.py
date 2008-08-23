# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et

from trac.core import *
from trac.web.api import IRequestFilter
#
#class L10NSystem(Component):

class TranslationCheckersInterface(Interface):

    def check(self, babel_msgid_object):
        "return an error message"
        return babel_msgid_object.check()

class L10NManager(Component):

    implements(IRequestFilter)

    checkers = ExtensionPoint(TranslationCheckersInterface)

    # IRequestFilter methods
    def pre_process_request(self, req, handler):
        return handler

    def post_process_request(self, req, template, data, content_type):
        data['l10nman'] = self
        return template, data, content_type

    def is_admin(self, req):
        return 'L10N_ADMIN' in req.perm

    def is_manager(self, req, locale):
        return req.authname in locale.admins

    def is_author(self, req, translation):
        return translation.sid == req.authname

    def can_translate(self, req):
        return 'L10N_ADD' in req.perm

    def can_delete_translation(self, req, translation):
        return self.is_author(req, translation) or \
               self.is_manager(req, translation.locale) or \
               self.is_admin(req)

    def check_translation(self, babel_msgid_object):
        errors = []
        for checker in self.checkers:
            error = checker.check(babel_msgid_object)
            if error:
                errors.append(error)

        return errors
