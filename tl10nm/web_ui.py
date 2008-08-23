# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8

import random
import re

from genshi.builder import tag

from trac.core import *
from trac.util.presentation import Paginator
from trac.util.translation import _
from trac.web import IRequestHandler
from trac.web.chrome import INavigationContributor, ResourceNotFound
from trac.web.chrome import add_link, add_stylesheet, add_script
from trac.web.chrome import Chrome
from trac.web.main import RequestDone

from tracext.sa import session

from tl10nm.api import L10NManager
from tl10nm.model import *

domain = 'tl10nm_messages'

class L10nModule(Component):
    implements(INavigationContributor, IRequestHandler)
    env = log = config = None # make pylint happy

    def __init__(self):
        Component.__init__(self)
        self.manager = L10NManager(self.env)

    # IPermissionRequestor
    def get_permission_actions(self):
        actions = ['L10N_ADD', 'L10N_DELETE', 'L10N_MODERATE']
        return actions + [('L10N_ADMIN', actions)]

    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return 'translations'

    def get_navigation_items(self, req):
        if 'L10N_VIEW' in req.perm:
            yield ('mainnav', 'translations',
                   tag.a('Translations', href=req.href.translations()))

    # IRequestHandler methods
    def match_request(self, req):
        match = re.match(r'^/(translate|translation|translations)+(?:/(.*))?$',
                         req.path_info)
        if match:
            return True
        return False

    def process_request(self, req):
        req.perm.require('L10N_VIEW')
        add_script(req, 'tl10nm/js/tl10nm.js')
        add_script(req, 'tl10nm/js/jquery.jTipNG.js')
        add_script(req, 'tl10nm/js/jquery.blockUI.js')
        add_stylesheet(req, 'tl10nm/css/l10n_style.css')

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
            data = {'projects': Session.query(Project).all()}
            return 'l10n_catalogs_list.html', data, None

        if not locale_name:
            # List available locales
            catalog = Session.query(Catalog).get(int(catalog_id))
            if not catalog:
                req.redirect(req.href.translations())
            data = {'catalog': catalog}
            return 'l10n_locales_list.html', data, None

        # List messages of specified locale
        catalog_id, page = int(catalog_id), int(page or 1)

        locale = Session.query(Locale).filter_by(locale=locale_name,
                                                 catalog_id=catalog_id).first()

        if not locale:
            req.redirect(req.href.translations(catalog_id))

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
            add_link(req, 'next', req.href.translations(catalog_id,
                                                        locale_name, page+1),
                     _('Next Page'))
        if paginator.has_previous_page:
            add_link(req, 'prev', req.href.translations(catalog_id,
                                                        locale_name, page-1),
                     _('Previous Page'))

        return 'l10n_messages.html', data, None

    def process_translation_request(self, req):
        match = re.match(r'^/translation'
                         r'(?:/([a-z_]+)?)?'  # action (vote up/down mark fuzzy)
                         r'(?:/([0-9]+)?)?',   # translation id
                         req.path_info)
        if not match:
            raise ResourceNotFound("Bad URL")

        redirect_back = req.args.get('redirect_back', req.href.translations())

        action, translation_id = match.groups()

        ajax_request = req.get_header('X-Requested-With')
        self.log.debug('Got an AJAX Request: %r', req.args)

        Session = session(self.env)

        translation = Session.query(Translation).get(int(translation_id))
        data = {'translation': translation, 'redirect_back': redirect_back}

        sid_voted = translation.votes.filter_by(sid=req.authname).first()

        html_template = 'l10n_vote_td_snippet.html'

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
            error = _("Not counting your vote. You already voted once.")
            vote = action=='vote_up' and 1 or -1
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
        elif action == 'mark_fuzzy':
            translation.fuzzy = True
            Session.commit()
            html_template = 'l10n_translation_td_snippet.html'
        elif action == 'delete':
            # Force a browser cache ignore
            req.send_header('Expires', 'Fri, 01 Jan 1999 00:00:00 GMT')
            html_template = 'l10n_translation_td_snippet.html'
            data['translation'] = None
            Session.delete(translation)
            Session.commit()
        else:
            raise ResourceNotFound("Bad URL")

        if ajax_request:
            # Return a partial render
            chrome = Chrome(self.env)
            output = chrome.render_template(req, html_template, data,
                                            fragment=True)
            req.write(output.render())
            raise RequestDone
        else:
            req.redirect(redirect_back)

    def process_translate_request(self, req):
        req.perm.require('L10N_ADD')
        match = re.match(r'^/translate'
                         r'(?:/([0-9]+)?)?'         # catalog id
                         r'(?:/([A-Za-z\-_]+)?)?'   # locale name
                         r'(?:/([0-9]+)?)?',        # msgid id
                         req.path_info)
        if not match:
            raise ResourceNotFound("Bad URL")

        catalog_id, locale_name, msgid_id = match.groups()

        if not catalog_id or not locale_name:
            req.redirect(req.href.translations())

        catalog_id = int(catalog_id)

        Session = session(self.env)

        locale = Session.query(Locale).filter_by(locale=locale_name,
                                                 catalog_id=catalog_id).first()

        data = {'catalog_id': catalog_id, 'locale': locale}


        data['translated'] = locale.translations.filter_by(
                                                    sid=req.authname).count()
        catalog = Session.query(Catalog).get(catalog_id)
        ids = [m.id for m in catalog.messages.all() if not
               m.translations.filter(
                    translation_table.c.sid!=req.authname).filter(
                        translation_table.c.locale_id==locale.id).all()]
        ids = [m.id for m in catalog.messages.all() if not
               m.translations.filter_by(locale_id=locale.id).all()]
        data['translatable'] = len(ids)
        data['max_translatable'] = locale.catalog.messages.count()

        if not msgid_id:
            random_id = random.choice(ids)
            self.log.debug("Randomly chose id %s from %s", random_id, ids)
            # Provide a random translation to the user
            data['message'] = message = Session.query(MsgID).get(random_id)
            # Force a browser cache ignore to get a new id in case user hits
            # reload.
            req.send_header('Expires', 'Fri, 01 Jan 1999 00:00:00 GMT')
        else:
            data['message'] = message = Session.query(MsgID).get(int(msgid_id))


        if req.method == 'POST':
            babel_message = message.babelize(locale)
            if message.plural:
                strings = []
                for idx in range(locale.num_plurals):
                    strings.append(req.args.get('translation-%d' % idx))
                babel_message.string = tuple(strings)
            else:
                babel_message.string = req.args.get('translation')

            # Babel Checks
            errors = babel_message.check()
            # Aditional L10NManger extension point checkers
            errors.extend(self.manager.check_translation(babel_message))

            if errors:
                req.args['form_fill'] = True # Fill in the form for us
                data['translation_errors'] = tag.ul(*[tag.li(e) for e
                                                      in errors])
                return 'l10n_translate_message.html', data, None

            translation = Translation(locale, message, req.authname)
            comment = req.args.get('comment')
            if comment:
                translation.comments.append(TranslationComment(translation,
                                                               comment))
            if message.plural:
                for idx in range(locale.num_plurals):
                    string = req.args.get('translation-%d' % idx)
                    translation.strings.append(
                                    TranslationString(translation, string, idx))
            else:
                translation.strings.append(
                                TranslationString(translation,
                                                  req.args.get('translation')))
            Session.save(translation)
            Session.commit()
            # Redirect back to locale translations
            req.redirect(req.href.translations(catalog_id, locale_name))
        return 'l10n_translate_message.html', data, None



