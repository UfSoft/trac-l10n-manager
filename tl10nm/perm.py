# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8

from trac.core import *
from trac.perm import IPermissionRequestor, PermissionSystem, PermissionError
from trac.perm import IPermissionPolicy
from trac.web import IRequestHandler
from trac.web.chrome import ITemplateProvider, INavigationContributor

class L10nPermissions(Component):
    implements(IPermissionRequestor)

    # IPermissionRequestor
    def get_permission_actions(self):
        actions = ['L10N_VIEW', 'L10N_ADD', 'L10N_DELETE', 'L10N_MODERATE']
        return actions + [('L10N_ADMIN', actions)]
