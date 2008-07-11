# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8

import re

from genshi.builder import tag

from trac.core import *
from trac.util.presentation import Paginator
from trac.util.translation import _
from trac.web import IRequestHandler, IRequestFilter, ITemplateStreamFilter
from trac.web.chrome import INavigationContributor, ResourceNotFound
from trac.web.chrome import add_link, add_stylesheet, add_script, add_ctxtnav
from trac.web.chrome import add_warning, add_notice, Chrome
from trac.web.main import RequestDone

from tsab import session

from tl10nm.model import *

class L10nModule(Component):
    implements(INavigationContributor, IRequestHandler) #, IRequestFilter)

    # IPermissionRequestor
    def get_permission_actions(self):
        actions = ['L10N_ADD', 'L10N_DELETE', 'L10N_MODERATE']
        return actions + [('L10N_ADMIN', actions)]

    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return 'translations'

    def get_navigation_items(self, req):
        yield ('mainnav', 'translations',
               tag.a('Translations', href=req.href.translations()))

    # IRequestFilter methods

    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info.startswith('/translate') or \
            req.path_info.startswith('/translation')

    def process_request(self, req):
        add_stylesheet(req, 'tl10nm/css/l10n_style.css')
        add_script(req, 'tl10nm/js/tl10nm.js')

        if req.path_info.startswith('/translations'):
            return self.process_translations_request(req)
        elif req.path_info.startswith('/translation'):
            return self.process_translation_request(req)
        elif req.path_info.startswith('/translate'):
            return self.process_translate_request(req)

    def process_translations_request(self, req):
        match = re.match(r'^/translations'
                         r'(?:/([0-9]+)?)?'         # catalog id
                         r'(?:/([A-Za-z\-_]+)?)?'   # locale name
                         r'(?:/([0-9]+)?)?',        # page
                         req.path_info)
        if not match:
            raise ResourceNotFound("Bad URL")

        catalog_id, locale_name, page = match.groups()

        Session = session(self.env)
        if not catalog_id:
            # List available catalogs
            data = {'catalogs': Session.query(Catalog).all()}
            return 'l10n_catalogs_list.html', data, None

        if not locale_name:
            # List available locales
            data = {'catalog': Session.query(Catalog).get(int(catalog_id))}
            return 'l10n_locales_list.html', data, None

        # List messages of specified locale
        return self._list_messages(req, int(catalog_id), locale_name,
                                   int(page or 1))

    def process_translation_request(self, req):
        match = re.match(r'^/translation'
                         r'(?:/([a-z_]+)?)?'  # action (vote up/down mark fuzzy)
                         r'(?:/([0-9]+)?)?',   # translation id
                         req.path_info)
        if not match:
            raise ResourceNotFound("Bad URL")

        vote = 0

        action, translation_id = match.groups()

        if action in ['vote_up', 'vote_down']:
            if action == 'vote_up':
                vote += 1
            else:
                vote -= 1
        elif action == 'remove_vote':
            pass
        elif action == 'mark_fuzzy':
            pass
        else:
            raise ResourceNotFound("Bad URL")

        ajax_request = req.get_header('X-Requested-With')
        self.log.debug('Got an AJAX Request: %r', req.args)

        Session = session(self.env)

        translation = Session.query(Translation).get(int(translation_id))
        data = {'translation': translation}

        sid_voted = translation.votes.filter_by(sid=req.authname).first()

        if action == 'remove_vote':
            if not sid_voted:
                error = _("You didn't vote for this translation")
                if ajax_request:
                    data['error'] = error
                else:
                      raise TracError(error)
            else:
                Session.delete(sid_voted)
                Session.commit()
        elif action in ['vote_up', 'vote_down']:
            error = _("Not counting your vote. You already voted")
            if not sid_voted:
                translation.votes.append(TranslationVote(translation,
                                                         req.authname, vote))
                Session.commit()

            else:
                if sid_voted.vote == vote:
                    # This must be a hand made request, a bad one
                    if ajax_request:
                        # Set error to be rendered
                        data['error'] = error
                    else:
                        raise TracError(error)
                else:
                    # User is changing his vote
                    sid_voted.vote = vote
                    Session.commit()

        if ajax_request:
            # Return a partial render
            chrome = Chrome(self.env)
            output = chrome.render_template(req, 'l10n_vote_td_snippet.html',
                                            data, fragment=True)
            # Don't forget to include the form token to keep trac happy
            if req.form_token:
                output |= chrome._add_form_token(req.form_token)
            req.write(output.render())
            raise RequestDone
        else:
            host = req.get_header('host')
            referer = req.get_header('referer')
            if referer:
                redirect_back = referer.split(host)[-1]
            else:
                redirect_back = req.href.translations()
            req.redirect(redirect_back)

    def process_translate_request(self, req):
        match = re.match(r'^/translations'
                         r'(?:/([0-9]+)?)?'         # catalog id
                         r'(?:/([A-Za-z\-_]+)?)?'   # locale name
                         r'(?:/([0-9]+)?)?',        # msgid id
                         req.path_info)
        if not match:
            raise ResourceNotFound("Bad URL")

        catalog_id, locale_name, msgid_id = match.groups()

        if not catalog_id or not locale_name:
            req.redirect(req.href.translations())
        if msgid_id:
            return self._translate_msgid(req, int(catalog_id), locale_name,
                                         int(msgid_id))


    # Internal Methods
    def _translate_msgid(self, req, catalog_id, locale_name, msgid_id):
        print req.__dict__.keys()
        print req.environ
        Session = session(self.env)

        self.env.db = Session # keep db connection opened as long as possible
        options = eagerload('translations')
        locale = Session.query(Locale).filter_by(locale=locale_name,
                                                 catalog_id=catalog_id).first()
        message = Session.query(MsgID).get(msgid_id)
        data = {'message': message, 'catalog_id': catalog_id,
                'locale': locale}

        for translation in message.translations(locale_id=locale.id):
            voter=translation.votes.filter_by(sid=req.authname).first()
            print '\n\n', repr(voter.sid), repr(voter.vote)
        return 'l10n_translate_message.html', data, None

    def _list_messages(self, req, catalog_id, locale_name, page):
        Session = session(self.env)
        locale = Session.query(Locale).filter_by(locale=locale_name,
                                                 catalog_id=catalog_id).first()

        data = {'locale': locale, 'catalog_id': catalog_id}

        paginator = Paginator(list(locale.catalog.messages), page-1, 5)
        data['messages'] = paginator
        shown_pages = paginator.get_shown_pages(25)
        pagedata = []
        for show_page in shown_pages:
            page_href = req.href.translations(catalog_id, locale_name,
                                              show_page)
            pagedata.append([page_href, None, str(show_page),
                             'page %s' % show_page])
        fields = ['href', 'class', 'string', 'title']
        paginator.shown_pages = [dict(zip(fields, p)) for p in pagedata]
        paginator.current_page = {'href': None, 'class': 'current',
                                  'string': str(paginator.page + 1),
                                  'title':None}
        if paginator.has_next_page:
            add_link(req, 'next', req.href.translations(locale_id, page+1),
                     _('Next Page'))
        if paginator.has_previous_page:
            add_link(req, 'prev', req.href.translations(locale_id, page-1),
                     _('Previous Page'))
        return 'l10n_messages.html', data, None

    def _translate_locale(self, req, catalog_id, locale_name):
        locale = session(self.env).query(Locale).filter_by(locale=locale_name,
                                                 catalog_id=catalog_id).first()
#        paginator = Paginator(locale.catalog.messages,
        data = {'locale': locale}
        return 'l10n_messages.html', data, None





