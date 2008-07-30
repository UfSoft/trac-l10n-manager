# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et

from trac.core import *
from trac.admin.api import IAdminPanelProvider
from trac.util.translation import _
from trac.web.chrome import add_notice, add_script

from genshi.builder import tag
from tracext.sa import session

from tl10nm.model import *

class L10NAdminProjects(Component):
    implements(IAdminPanelProvider)
    env = log = config = None # make pylint happy

    # IAdminPageProvider methods
    def get_admin_panels(self, req):
        if 'L10N_ADMIN' in req.perm:
            yield ('translations', 'L10N Manager', 'projects', _('Projects'))

    def render_admin_panel(self, req, cat, page, path_info):
        req.perm.require('L10N_MODERATE', 'L10N_ADMIN', 'TRAC_ADMIN')
        add_script(req, 'tl10nm/js/tl10nm.js')
        add_script(req, 'tl10nm/js/jquery.jTipNG.js')
        # add_stylesheet(req, 'tl10nm/css/l10n_style.css')
        # Needs to be on the template so that trac's admin.css get's overridden

        if cat == 'translations' and page == 'projects':
            data = {}
            if req.method == 'POST':
                if req.args.get('delete_selected'):
                    data.update(self.delete_project(req))
                elif req.args.get('add_project'):
                    data.update(self.add_project(req))

            Session = session(self.env)
            projects = data['projects'] = Session.query(Project).all()

            return 'l10n_admin_projects.html', data

    def add_project(self, req):
        data = {}
        errors = []

        data['name'] = name = req.args.get('name')
        data['domain'] = domain = req.args.get('domain')
        data['copyright'] = copyright = req.args.get('copyright')
        data['bugs_address'] = bugs_address = req.args.get('bugs_address')

        def add_error(error):
            errors.append(error)
            data['error'] = tag.ul(*[tag.li(e) for e in errors if e])
            return data

        if not name:
            add_error(_('You must define a project name'))
        if not domain:
            add_error(_('You must define a catalog domain'))

        if errors:
            return add_error('')

        Session = session(self.env)

        if Session.query(Project).filter(project_table.c.name==name).first():
            return add_error(_('A project with that name exists. '
                               'Please choose another one'))

        project = Project(name, domain, copyright, bugs_address)
        Session.save(project)
        Session.commit()
        return data

    def delete_project(self, req):
        pass
