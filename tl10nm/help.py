# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8

import os
import re

from weakref import WeakValueDictionary

from trac.core import *
from trac.web import IRequestHandler
from trac.web.chrome import Chrome
from trac.web.main import RequestDone, ResourceNotFound
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

        ajax_request = req.get_header('X-Requested-With')
        data['ajax_request'] = ajax_request

        if not self.template_available(template):
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
        valid_template = self.available_templates.get(template)
        if valid_template is None:
            template_path = resource_filename(
                __name__, os.path.join('templates', *(template.split('/')))
            )
            if os.path.exists(template_path):
                self.available_templates[template] = True
                return True
        return valid_template
