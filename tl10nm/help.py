# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8

from datetime import datetime
import os
import re

from weakref import WeakValueDictionary

from trac.core import *
from trac.web import IRequestHandler
from trac.web.chrome import Chrome
from trac.web.main import RequestDone, ResourceNotFound
from trac.util.datefmt import localtz
from trac.util.translation import _

from genshi.builder import tag
from genshi.template import TemplateNotFound
from pkg_resources import resource_filename


class WeakReferenceRenderer(object):
    def __init__(self, env, template, data):
        self.env = env
        self.data = data
        self.template = template

    def render(self, req):
        chrome = Chrome(self.env)
        output = chrome.render_template(req, self.template,
                                        self.data, fragment=True)
        return output.render()


class L10NManagerHelpModule(Component):
    implements(IRequestHandler)

    available_templates = {}
    rendered_templates = WeakValueDictionary()

    # IRequestHandler methods
    def match_request(self, req):
        match = re.match(r'^/l10nhelp(?:/(.*))+$', req.path_info)
        if match:
            return True
        return False

    def process_request(self, req):
        match = re.match(r'^/l10nhelp/(.*)$', req.path_info)
        template = 'l10nhelp/%s.html' % match.group(1)
        data = {}

        data['ajax_request'] = ajax_request = \
            req.get_header('X-Requested-With') == 'XMLHttpRequest' and \
            req.args.get('ajax_request') == '1'

        last_modified = self.template_available(template)
        # Include cache headers to ease on server requests since this data does
        # not change
        req.check_modified(last_modified)

        if not last_modified:
            if ajax_request:
                req.write(tag.p(_("Help Not Found")))
                raise RequestDone
            raise ResourceNotFound(_("Help Not Found"))

        if not ajax_request:
            data.update( {'template': template} )
            return 'l10n_help_base.html', data, None

        output = self.rendered_templates.get(template)
        if output is None:
            output = WeakReferenceRenderer(self.env, template, data)
            self.rendered_templates[template] = output
        req.write(output.render(req))
        raise RequestDone

    # Internal method
    def template_available(self, template):
        last_modified = self.available_templates.get(template)
        if last_modified is None:
            template_path = resource_filename(
                __name__, os.path.join('templates', *(template.split('/')))
            )
            if os.path.exists(template_path):
                stat = os.stat(template_path)
                mtime = datetime.fromtimestamp(stat.st_mtime, localtz)
                self.available_templates[template] = mtime
                return self.available_templates[template]
        return last_modified
