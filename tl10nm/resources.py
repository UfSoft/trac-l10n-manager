# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8

from trac.core import *
from trac.web.chrome import ITemplateProvider

class L10nResources(Component):
    implements(ITemplateProvider)

    # ITemplateProvider methods
    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('tl10nm', resource_filename(__name__, 'htdocs'))]
