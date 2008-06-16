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

from trac.resource import ResourceNotFound
from trac.util.translation import _
from trac.versioncontrol import NoSuchChangeset
from trac.versioncontrol.web_ui.util import get_existing_node
from trac.web.main import RequestDone

from genshi.builder import tag

def ajax_return_repo_paths_list(env, req):
    repopath = req.args.get('q', '/')

    repos = env.get_repository(req.authname)

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
