# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8

from trac.core import Component, implements
from trac.web.api import ITemplateStreamFilter

from genshi.filters.html import HTMLFormFiller

class L10NFormsAutoFill(Component):
    implements(ITemplateStreamFilter)

    # ITemplateStreamFilter methods
    def filter_stream(self, req, method, filename, stream, data):
        if 'form_fill' in req.args:
            return stream | HTMLFormFiller(data=req.args)
        return stream
