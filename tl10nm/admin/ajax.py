# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et

import re
import posixpath
from operator import attrgetter

from trac.core import Component, implements, TracError
from trac.util.translation import _
from trac.versioncontrol import NoSuchNode
from trac.web.api import IRequestHandler
from trac.web.main import RequestDone

from genshi.builder import tag
from tracext.sa import session

from tl10nm.model import *
from tl10nm.admin.utils import AVAILABLE_LOCALES

class L10NAjaxRequests(Component):
    implements(IRequestHandler)
    env = log = config = None # make pylint happy

    # IRequestHandler
    def match_request(self, req):
        if not req.get_header('X-Requested-With'):
            return False
        match = re.match(r'^/translations/ajax(?:/([a-z_]+)?)?',
                         req.path_info)
        if match:
            self.log.debug('AJAX Request Match: %r', req.args)
            return True
        return False

    def process_request(self, req):
        req.perm.require('L10N_ADMIN') # 'L10N_MODERATE'

        match = re.match(r'^/translations/ajax(?:/([a-z_]+)?)?',
                         req.path_info)
        if not match:
            raise RequestDone

        request = 'handle_%s' % match.group(1)
        self.log.debug('AJAX Handler: %s', request)
        ajax_handler = getattr(self, request)
        if ajax_handler and callable(ajax_handler):
            return ajax_handler(req)
        raise RequestDone

    # Internal/Custom methods
    def handle_repo_paths(self, req):
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
            req.write(tag.center(
                tag.em(_("No matches found on repository for "),
                tag.b(repopath))
            ))
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

    def handle_locales(self, req):
        query = req.args.get('q')
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

    def handle_catalogs(self, req):
        project_id = req.args.get('q')
        project = session(self.env).query(Project).get(int(project_id))

        if not project:
            raise TracError

        if not project.catalogs:
            req.write(tag.em('No catalogs available'))
            raise RequestDone

        req.write('<select name="catalog_template">')
        for catalog in project.catalogs:
            req.write(tag.option(catalog.fpath, value=catalog.id))
        req.write('</select>')
        raise RequestDone
