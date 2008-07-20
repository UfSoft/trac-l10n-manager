# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8

import time

from babel import Locale as BabelLocale

import sqlalchemy as sqla
from sqlalchemy.orm import mapper, relation, dynamic_loader, backref, synonym
from sqlalchemy.orm import eagerload

from tracext.sa import session

name = 'trac-l10nmanager'
version = 1

metadata = sqla.MetaData()

catalog_table = sqla.Table('l10n_catalogs', metadata,
    sqla.Column('id', sqla.Integer, primary_key=True, autoincrement=True),
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

class Catalog(object):
    """Represents a catalog template"""
    def __init__(self, fpath, description, revision):
        self.fpath = fpath
        self.revision = revision
        self.description = description

class MsgID(object):
    """Represents a catalog's msgid"""
    def __init__(self, catalog, string, plural, context):
        self.catalog = catalog
        self.string = string
        self.plural = plural
        self.context = context

    def split(self, split_by):
        return self.string.split(split_by)


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

class LocaleAdmin(object):
    def __init__(self, locale, sid):
        self.locale = locale
        self.sid = sid

class Translation(object):
    """Represents a catalog's translation"""
    def __init__(self, locale, msgid, sid, fuzzy=False, created=None):
        self.locale = locale
        self.msgid = msgid
        self.sid = sid
        self.fuzzy = fuzzy
        self.created = created or int(time.time())

    @property
    def votes_count(self):
        return sum([v.vote for v in self.votes])

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
                      cascade='all, delete, delete-orphan')
))

mapper(LocaleAdmin, locale_admin_table)

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

mapper(TranslationString, translation_string_table)
mapper(TranslationComment, translation_comment_table)
mapper(TranslationVote, translation_vote_table)
