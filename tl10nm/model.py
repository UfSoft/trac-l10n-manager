# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8

import time
from tempfile import mkstemp

from babel import Locale as BabelLocale
from babel.messages.catalog import Catalog as BabelCatalog
from babel.messages.catalog import Message, DEFAULT_HEADER
from babel.messages.pofile import write_po
from babel.messages.mofile import write_mo

import sqlalchemy as sqla
from sqlalchemy.orm import mapper, relation, dynamic_loader, synonym
from sqlalchemy.orm.collections import InstrumentedList

from tracext.sa import session

name = 'trac-l10nmanager'
version = 1

metadata = sqla.MetaData()

project_table = sqla.Table('l10n_projects', metadata,
    sqla.Column('id', sqla.Integer, primary_key=True, autoincrement=True),
    sqla.Column('name', sqla.Text, nullable=False, unique=True),
    sqla.Column('domain', sqla.Text, nullable=False),
    sqla.Column('copyright', sqla.Text),
    sqla.Column('bugs_address', sqla.Text)
)

catalog_table = sqla.Table('l10n_catalogs', metadata,
    sqla.Column('id', sqla.Integer, primary_key=True, autoincrement=True),
    sqla.Column('project_id', None, sqla.ForeignKey('l10n_projects.id')),
    sqla.Column('fpath', sqla.Text, nullable=False),
    sqla.Column('description', sqla.Text),
    sqla.Column('revision', sqla.Integer)
)

msgid_table = sqla.Table('l10n_msgids', metadata,
    sqla.Column('id', sqla.Integer, primary_key=True, autoincrement=True),
    sqla.Column('catalog_id', None, sqla.ForeignKey('l10n_catalogs.id')),
    sqla.Column('string', sqla.Text, nullable=False),
    sqla.Column('plural', sqla.Text),
    sqla.Column('context', sqla.Text, default='')
)

msgid_location_table = sqla.Table('l10n_msgid_locations', metadata,
    sqla.Column('id', sqla.Integer, primary_key=True, autoincrement=True),
    sqla.Column('msgid_id', None, sqla.ForeignKey('l10n_msgids.id')),
    sqla.Column('fname', sqla.Text),
    sqla.Column('lineno', sqla.Integer),
    sqla.Column('href', sqla.Text),
    sqla.UniqueConstraint('msgid_id', 'fname', 'lineno'),
)

msgid_comment_table = sqla.Table('l10n_msgid_comments', metadata,
    sqla.Column('id', sqla.Integer, primary_key=True),
    sqla.Column('msgid_id', None, sqla.ForeignKey('l10n_msgids.id')),
    sqla.Column('comment', sqla.Text, nullable=False)
)

msgid_flag_table = sqla.Table('l10n_msgid_flags', metadata,
    sqla.Column('id', sqla.Integer, primary_key=True),
    sqla.Column('msgid_id', sqla.Integer, sqla.ForeignKey('l10n_msgids.id')),
    sqla.Column('flag', sqla.String(20), nullable=False)
)

locale_table = sqla.Table('l10n_locales', metadata,
    sqla.Column('id', sqla.Integer, primary_key=True),
    sqla.Column('locale', sqla.String(20), nullable=False),
    sqla.Column('catalog_id', None, sqla.ForeignKey('l10n_catalogs.id')),
    sqla.Column('num_plurals', sqla.Integer, nullable=False),
    sqla.UniqueConstraint('locale', 'catalog_id')
)

locale_admin_table = sqla.Table('l10n_locale_admins', metadata,
    sqla.Column('id', sqla.Integer, primary_key=True),
    sqla.Column('locale_id', None, sqla.ForeignKey('l10n_locales.id')),
    sqla.Column('sid', sqla.Text, nullable=False),
    sqla.UniqueConstraint('locale_id', 'sid')
)

translation_table = sqla.Table('l10n_translations', metadata,
    sqla.Column('id', sqla.Integer, primary_key=True),
    sqla.Column('locale_id', None, sqla.ForeignKey('l10n_locales.id')),
    sqla.Column('msgid_id', None, sqla.ForeignKey('l10n_msgids.id')),
    sqla.Column('sid', sqla.Text, nullable=False),
    sqla.Column('created', sqla.Integer),
    sqla.Column('fuzzy', sqla.Boolean),
    sqla.UniqueConstraint('locale_id', 'msgid_id', 'sid')
)

translation_string_table = sqla.Table('l10n_translation_strings', metadata,
    sqla.Column('id', sqla.Integer, primary_key=True),
    sqla.Column('translation_id', None, sqla.ForeignKey('l10n_translations.id')),
    sqla.Column('string', sqla.Text, nullable=False),
    sqla.Column('index', sqla.Integer, default=0),
    sqla.UniqueConstraint('translation_id', 'index')
)

translation_comment_table = sqla.Table('l10n_translation_comments', metadata,
    sqla.Column('id', sqla.Integer, primary_key=True),
    sqla.Column('translation_id', None, sqla.ForeignKey('l10n_translations.id')),
    sqla.Column('comment', sqla.Text, nullable=False)
)

translation_vote_table = sqla.Table('l10n_translation_votes', metadata,
    sqla.Column('id', sqla.Integer, primary_key=True),
    sqla.Column('translation_id', None, sqla.ForeignKey('l10n_translations.id')),
    sqla.Column('sid', sqla.Text, nullable=False),
    sqla.Column('vote', sqla.Integer, nullable=False),
    sqla.UniqueConstraint('translation_id', 'sid')
)

class Project(object):
    """Represents a localized project"""
    id = catalogs = None # Make pylint happy
    def __init__(self, name, domain, copyright='', bugs_address=''):
        self.name = name
        self.domain = domain
        self.copyright = copyright
        self.bugs_address = bugs_address

    @property
    def localized(self):
        localized = False
        for catalog in self.catalogs:
            if catalog.locales:
                localized = True
        return localized

    @property
    def mo_fname(self):
        return "%s.mo" % self.domain

    @property
    def po_fname(self):
        return "%s.po" % self.domain

class Catalog(object):
    """Represents a catalog template"""
    id = messages = locales = None # Make pylint happy
    def __init__(self, project, fpath, description, revision):
        self.project = project
        self.fpath = fpath
        self.revision = revision
        self.description = description

class MsgID(object):
    """Represents a catalog's msgid"""
    id = locations = comments = flags = translations = None # Make pylint happy
    def __init__(self, catalog, string, plural, context):
        self.catalog = catalog
        self.string = string
        self.plural = plural
        self.context = context

    def is_translator(self, locale, sid):
        return self.translations.filter(
            msgid_table.c.id==self.id).filter_by(
                sid=sid).filter_by(locale_id=locale.id).first()

    def split(self, split_by):
        return self.string.split(split_by)

    def get_highest_voted_translation(self, locale):
        translations = self.translations.filter(msgid_table.c.id==self.id). \
                                            filter_by(locale_id=locale.id).all()
        if not translations:
            return None

        votes = -1
        higher_votes_translation = None
        for translation in translations:
            # SQL Sort translations by votes?
            if translation.votes_count > votes:
                higher_votes_translation = translation
        return higher_votes_translation

    def babelize(self, locale):
        locations = [(l.fname, l.lineno) for l in self.locations]
        flags = [f.flag for f in self.flags]
        auto_comments = [c.comment for c in self.comments]

        if self.plural:
            msgid = self.string, self.plural
        else:
            msgid = self.string

        strings, user_comments = '', []
        translation = self.get_highest_voted_translation(locale)
        if translation:
            strings, user_comments = translation.babelize()

        message = Message(msgid, string=strings, locations=locations,
                          flags=flags, auto_comments=auto_comments,
                          user_comments=user_comments)
        return message

class MsgIDLocation(object):
    """Represents the catalog's msgid location on source"""
    def __init__(self, msgid, fname, lineno, href):
        self.msgid = msgid
        self.fname = fname
        self.lineno = lineno
        self.href = href


class MsgIDComment(object):
    """Represents a catalog's msgid comment"""
    def __init__(self, msgid, comment):
        self.msgid = msgid
        self.comment = comment

    def split(self, split_by):
        return self.comment.split(split_by)

class MsgIDFlag(object):
    """Represents a catalog's msgid flag"""
    def __init__(self, msgid, flag):
        self.msgid = msgid
        self.flag = flag

    def __str__(self):
        return self.flag

    def __unicode__(self):
        return self.__str__()

class Locale(object):
    """Represents a locale catalog"""
    id = translations = admins = None # Make pylint happy
    def __init__(self, catalog, locale, num_plurals):
        self.catalog = catalog
        self.locale = locale
        self.num_plurals = num_plurals

    def _get_locale(self):
        return BabelLocale.parse(self._locale)
    def _set_locale(self, value):
        self._locale = str(BabelLocale.parse(value))
    locale = property(_get_locale, _set_locale)
    del _get_locale, _set_locale

    @property
    def translated(self):
        return self.translations.filter_by(fuzzy=False).count()

    @property
    def translated_percent(self):
        return self.translated * 100.0 / self.catalog.messages.count()
    @property
    def untranslated(self):
        return self.catalog.messages.count() - self.translated - self.fuzzy
    @property
    def untranslated_percent(self):
        return self.untranslated * 100.0 / self.catalog.messages.count()
    @property
    def fuzzy(self):
        return self.translations.filter_by(fuzzy=True).count()
    @property
    def fuzzy_percent(self):
        return self.fuzzy * 100.0 / self.catalog.messages.count()

    @property
    def contributors(self):
        contributors = []
        for translation in self.translations.all():
            if translation.sid not in contributors:
                contributors.append(translation.sid)
        return contributors

    def _build_catalog(self):
        project = self.catalog.project
        name = project.name
        domain = project.domain
        copyright = project.copyright
        bugs_address = project.bugs_address
        last_translator = None
        contributors = []
        messages = self.catalog.messages.filter_by(catalog_id=self.catalog.id)
        from datetime import datetime
        for message in messages:
            translation = message.get_highest_voted_translation(self)
            if translation:
                sid = translation.sid
                ts = datetime.utcfromtimestamp(translation.created).strftime('%Y')
                if (sid, ts) not in contributors:
                    contributors.append((sid, ts))
        HEADER = DEFAULT_HEADER.splitlines()[:-2]
        if contributors:
            HEADER.extend(['#', '# Contributors:'] +
                          ['# %s, %s' % sid for sid in contributors])
            last_translator = contributors[-1][0]
        HEADER.append('#')
        catalog = BabelCatalog(self.locale, domain, header_comment='\n'.join(HEADER),
                               project=name,
                               copyright_holder=copyright,
                               msgid_bugs_address=bugs_address,
                               fuzzy=False,
                               last_translator=last_translator)
        for message in messages:
            catalog[message.id] = message.as_babel_message(self)
        return catalog

    def get_pofile(self):
        tempfile = mkstemp('.txt')
        catalog = self._build_catalog()
        write_po(open(tempfile[1], 'w'), catalog)
        return tempfile

    def get_mofile(self):
        catalog = self._build_catalog()
        tempfile = mkstemp('.mo')
        fileobj = open(tempfile[1], 'w')
        write_mo(fileobj, catalog, use_fuzzy=False)
        return tempfile


class LocaleAdmin(object):
    id = locales = None # Make pylint happy
    def __init__(self, locale, sid):
        self.locale = locale
        self.sid = sid

class Translation(object):
    """Represents a catalog's translation"""
    id = strings = comments = votes = None # Make pylint happy
    def __init__(self, locale, msgid, sid, fuzzy=False, created=None):
        self.locale = locale
        self.msgid = msgid
        self.sid = sid
        self.fuzzy = fuzzy
        self.created = created or int(time.time())

    @property
    def votes_count(self):
        return sum([v.vote for v in self.votes])

    def babelize(self):
        strings = [s.string for s in self.strings]
        if len(strings) < 2:
            strings = strings[0]
        else:
            strings = tuple(strings)
        return strings, [uc.comment for uc in self.comments]

class TranslationString(object):
    """Represents a catalog's translation string"""
    def __init__(self, translation, string, index=0):
        self.translation = translation
        self.string = string
        self.index = index

    def split(self, split_by):
        return self.string.split(split_by)

class TranslationComment(object):
    """Represents a transtor's comment"""
    def __init__(self, translation, comment):
        self.translation = translation
        self.comment = comment

    def split(self, split_by):
        return self.comment.split(split_by)

class TranslationVote(object):
    """Represents a vote to a translation"""

    def __init__(self, translation, sid, vote):
        self.translation = translation
        self.sid = sid
        self.vote = vote

class OverridenInstrumentedList(InstrumentedList):
    __attr_to_get__ = 'sid'

    def __contains__(self, obj):
        for rec in self:
            if hasattr(rec, self.__attr_to_get__):
                if getattr(rec, self.__attr_to_get__) == obj:
                    return True
        return InstrumentedList.__contains__(self, obj)

    def __call__(self, attr_to_get):
        attr_results = []
        for rec in self:
            if hasattr(rec, attr_to_get):
                attr_results.append(getattr(rec, attr_to_get))
        return attr_results


mapper(Project, project_table, properties=dict(
    catalogs = relation(Catalog, backref='project', lazy=False,
                        cascade='all, delete, delete-orphan'),
))

mapper(Catalog, catalog_table, properties=dict(
    messages = dynamic_loader(MsgID, backref='catalog',
                        cascade='all, delete, delete-orphan'),
    locales = relation(Locale, backref='catalog', #lazy=False,
                       cascade='all, delete, delete-orphan')
))

mapper(Locale, locale_table, properties=dict(
    translations = dynamic_loader(Translation, backref='locale',
                                  cascade='all, delete, delete-orphan'),
    locale = synonym('_locale', map_column=True),
    admins = relation(LocaleAdmin, backref='locale',
                      collection_class=OverridenInstrumentedList,
                      cascade='all, delete, delete-orphan')
))

mapper(LocaleAdmin, locale_admin_table, properties=dict(
    locales = relation(Locale, backref='admin')
))

mapper(MsgID, msgid_table, properties=dict(
    locations = relation(MsgIDLocation, backref='msgid', #lazy=False,
                         cascade='all, delete, delete-orphan',
                         order_by=[msgid_location_table.c.fname,
                                   msgid_location_table.c.lineno]),
    comments = relation(MsgIDComment, backref='msgid',
                        cascade='all, delete, delete-orphan'),
    flags = relation(MsgIDFlag, backref='msgid',
                     cascade='all, delete, delete-orphan'),
    translations = dynamic_loader(Translation, backref='msgid',
                                  order_by=[translation_table.c.created])
))

mapper(MsgIDLocation, msgid_location_table)
mapper(MsgIDComment, msgid_comment_table)
mapper(MsgIDFlag, msgid_flag_table)

mapper(Translation, translation_table, properties=dict(
    strings = relation(TranslationString, backref='translation',
                       cascade='all, delete, delete-orphan'),
    comments = relation(TranslationComment, backref='translation',
                        cascade='all, delete, delete-orphan'),
    votes = dynamic_loader(TranslationVote, backref='translation',
                           cascade='all, delete, delete-orphan')
))

mapper(TranslationString, translation_string_table,
       order_by=[translation_string_table.c.translation_id,
                 translation_string_table.c.index,
                 translation_string_table.c.string])

mapper(TranslationComment, translation_comment_table,
       order_by=[translation_comment_table.c.translation_id,
                 translation_comment_table.c.comment])
mapper(TranslationVote, translation_vote_table)
