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

import time
from copy import copy

from babel.messages.plurals import PLURALS

class CatalogTemplate(object):
    _fpath = None
    fpath = None
    _revision = None
    revision = None
    def __init__(self, env, fpath='', revision=''):
        self.env = env
        self.fpath = fpath
        self.revision = revision
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT revision FROM l10n_catalogs WHERE fpath=%s ",
                       (self.fpath,))
        row = cursor.fetchone()
        if row:
            self.revision = row[0]

        self._fpath = copy(self.fpath)
        self._revision = copy(self.revision)

    def save(self):
        db = self.env.get_db_cnx()
        cursor = db.cursor()

#        if self.fpath != self._fpath or self.revision != self._revision:

        cursor.execute("UPDATE l10n_catalogs SET fpath=%s, revision=%s WHERE "
                       "fpath=%s AND revision=%s",
                       (self.fpath, self.revision, self._fpath, self._revision))
        if not cursor.rowcount:
            cursor.execute("INSERT INTO l10n_catalogs "
                           "(fpath, revision) VALUES (%s, %s)",
                           (self.fpath, self.revision))
        db.commit()

    @property
    def locales(self):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT id from l10n_locales WHERE template=%s",
                       (self.fpath,))
        locales = []
        for id in cursor:
            locales.append(Catalog.get_by_id(self.env, id))
        return locales

    @property
    def messages(self):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT DISTINCT l10n_messages.msgid, l10n_messages.id "
                       "FROM l10n_messages INNER JOIN l10n_locations ON "
                       "(l10n_locations.msgid_id=l10n_messages.id) "
                       "WHERE template=%s ORDER BY l10n_locations.fname,"
                       "l10n_locations.lineno,l10n_messages.msgid ",
                       (self.fpath,))
        messages = []
        for msgid, id in cursor:
            msg = Message.get_by_id(self.env, id)
            messages.append(msg)
        return messages

    def delete(self):
        for locale in self.locales:
            locale.delete()
        for msg in self.messages:
            msg.delete()
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("DELETE FROM l10n_catalogs WHERE fpath=%s", (self.fpath,))
        db.commit()

#    @classmethod
#    def get_by_id(cls, env, id):
#        db = env.get_db_cnx()
#        cursor = db.cursor()
#        cursor.execute("SELECT locale, fpath, revision FROM "
#                       "l10n_catalogs WHERE id=%s", (id,))
#        row = cursor.fetchone()
#        if not row:
#            return None
#        return Catalog(env, *row)
#
    @classmethod
    def get_all(cls, env):
        db = env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT fpath, revision FROM l10n_catalogs")
        catalog_templates = []
        for fpath, revision in cursor:
            catalog_templates.append(CatalogTemplate(env, fpath, revision))
        return catalog_templates

class LocaleCatalog(object):
    id = None
    plurals = 1
    def __init__(self, env, locale='', fpath='', revision='', template=''):
        self.env = env
        self.locale = locale
        self.fpath = fpath
        self.revision = revision
        self.template = template
        exists = self.refresh()
        if not exists:
            if locale in PLURALS:
                self.plurals = PLURALS[locale][0]
            elif '_' in locale:
                loc = locale.split('_')[0]
                if loc in PLURALS:
                    self.plurals = PLURALS[loc][0]
#        self.refresh()


    def refresh(self):
#        print "refreshing LocaleCatalog for locale: %s" % self.locale, self.__dict__
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT id, template, plurals, revision FROM "
                       "l10n_locales WHERE locale=%s AND fpath=%s",
                       (self.locale, self.fpath))
        row = cursor.fetchone()
        if row:
            self.id, self.template, self.plurals, self.revision = row
#            print 'refreshed'
            return True
#        print 'non existing'
        return False

    def save(self):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("UPDATE l10n_locales SET template=%s, locale=%s, "
                       "fpath=%s, plurals=%s, revision=%s WHERE id=%s",
                       (self.template, self.locale, self.fpath,
                        self.plurals, self.revision, self.id))
        if not cursor.rowcount:
            cursor.execute("INSERT INTO l10n_locales "
                           "(template, locale, fpath, plurals, revision) "
                           " VALUES (%s, %s, %s, %s, %s)",
                           (self.template, self.locale, self.fpath,
                            self.plurals, self.revision))
        db.commit()
        self.refresh()

    def update_stats(self):
        fuzzy = len(self.fuzzy)
        translated = len(self.translated) - fuzzy
        untranslated = len(self.untranslated)
        max_value = fuzzy + translated + untranslated
        fuzzy_percent = fuzzy * 100 / max_value
        translated_percent = translated * 100 / max_value
        untranslated_percent = untranslated * 100 / max_value

        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("UPDATE l10n_locale_stats SET translated=%s, "
                       "translated_percent=%s, fuzzy=%s, fuzzy_percent=%s, "
                       "untranslated=%s, untranslated_percent=%s WHERE "
                       "locale_id=%s",
                       (translated, translated_percent, fuzzy, fuzzy_percent,
                        untranslated, untranslated_percent, self.id))
        if not cursor.rowcount:
            cursor.execute("INSERT INTO l10n_locale_stats (locale_id, "
                           "translated, translated_percent, fuzzy, "
                           "fuzzy_percent, untranslated, untranslated_percent) "
                           "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                           (self.id, translated, translated_percent, fuzzy,
                            fuzzy_percent, untranslated, untranslated_percent))
        db.commit()

    @property
    def stats(self):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT translated, translated_percent, fuzzy, "
                       "fuzzy_percent, untranslated, untranslated_percent "
                       "FROM l10n_locale_stats WHERE locale_id=%s",
                       (self.id,))
        return cursor.fetchone()


    @property
    def messages(self):
        template = CatalogTemplate(self.env, self.template)
        return template.messages

    @property
    def translated(self):
        translated = []
        for message in self.messages:
            for translation in message.translations(self.id):
                if translation.string:
                    translated.append(message)
        return translated

    @property
    def untranslated(self):
        untranslated = []
        for message in self.messages:
            for translation in message.translations(self.id):
                if not translation.string:
                    untranslated.append(message)
        return untranslated

    @property
    def fuzzy(self):
        fuzzy = []
        for message in self.translated:
            for translation in message.translations(self.id):
                if 'fuzzy' in translation.flags:
                    fuzzy.append(message)
        return fuzzy


    def delete(self):
        for msg in self.messages:
            for translation in msg.translations(self.id):
                translation.delete()

        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("DELETE FROM l10n_locale_stats WHERE locale_id=%s",
                       (self.id,))
        cursor.execute("DELETE FROM l10n_locales WHERE id=%s", (self.id,))
        db.commit()

    @classmethod
    def get_by_id(cls, env, id):
        db = env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT locale, fpath, revision, template FROM "
                       "l10n_locales WHERE id=%s", (id,))
        row = cursor.fetchone()
        if not row:
            return None
        return LocaleCatalog(env, *row)

    @classmethod
    def get_all(cls, env): #, locale=None, no_empty_locale=False):
        db = env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT locale, fpath, revision, template FROM "
                       "l10n_locales")
        catalogs = []
        for locale, fpath, revision, template in cursor:
            catalogs.append(LocaleCatalog(env, locale, fpath, revision,
                                          template))
        return catalogs

class Message(object):
    id = None
    msgid = None
    plural = None
    flags = ''
    ac = ''
    previous_id = ''
    lineno = ''
    context = ''

    def __init__(self, env, template, msgid):
        self.env = env
        self.template = template
        self.msgid = msgid

        db = env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT id,plural,flags,ac,previous_id,lineno,context"
                       " FROM l10n_messages WHERE template=%s AND msgid=%s",
                       (template, msgid))
        row = cursor.fetchone()
        if row:
            self.id, self.plural, self.flags, self.ac, \
                self.previous_id, self.lineno, self.context = row
            self.flags = self.flags.split(',')


    def save(self):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("UPDATE l10n_messages SET plural=%s, flags=%s, ac=%s,"
                       "previous_id=%s, lineno=%s, context=%s WHERE msgid=%s AND template=%s",
                       (self.plural, ','.join(list(self.flags)), '\n'.join(self.ac),
                        '\n'.join(self.previous_id), self.lineno, self.context,
                        self.msgid, self.template))
        if not cursor.rowcount:
#            print 1
            cursor.execute("INSERT INTO l10n_messages (template,msgid,plural,"
                           "flags,ac,previous_id,lineno,context) VALUES (%s,%s,"
                           "%s,%s,%s,%s,%s,%s)",
                           (self.template, self.msgid, self.plural, ','.join(self.flags),
                            '\n'.join(self.ac), '\n'.join(self.previous_id), self.lineno,
                            self.context))
        db.commit()
        cursor.execute("SELECT id FROM l10n_messages WHERE msgid=%s AND "
                       "template=%s", (self.msgid, self.template))
        row = cursor.fetchone()
        if row:
            self.id = row[0]

    def delete(self):
        for location in self.locations:
            location.delete()
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("DELETE FROM l10n_messages WHERE "
                       "template=%s AND msgid=%s",
                       (self.template, self.msgid))
        db.commit()

    @classmethod
    def get_by_id(cls, env, id):
        db = env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT template, msgid FROM "
                       "l10n_messages WHERE id=%s", (id,))
        row = cursor.fetchone()
        if not row:
            return None
        return Message(env, *row)

    @property
    def locations(self):
        if not self.id:
            self.save()
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT msgid_id, fname, lineno from l10n_locations WHERE "
                       "msgid_id=%s ORDER BY fname, lineno", (self.id,))
        locs = []
        for row in cursor:
            location = Location(self.env, *row)
            locs.append(location)
        return locs
#    locations = property(locations)

    def add_translation(self, locale, msgstr, idx=0):
        assert isinstance(locale, LocaleCatalog)
        translation = Translation(self.env, locale.id, self.id, msgstr, idx)
        translation.save()

#    @property
    def translations(self, locale_id):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT string, idx FROM l10n_translations WHERE "
                       "locale_id=%s AND msgid_id=%s",
                       (locale_id, self.id))

        translations = []
        for string, idx in cursor:
            translation = Translation(self.env, locale_id, self.id, string, idx)
            translations.append(translation)
        return translations



class Location(object):
    id = None
    msgid_id = None
    fname = None
    lineno = None
    href = None

    def __init__(self, env, msgid_id, fname=None, lineno=None):
        self.env = env
        self.msgid_id = msgid_id
        self.fname = fname
        self.lineno = lineno
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT id, href FROM l10n_locations WHERE msgid_id=%s AND "
                       "fname=%s AND lineno=%s",
                       (self.msgid_id, self.fname, self.lineno))
        row = cursor.fetchone()
        if row:
            self.id, self.href = row

    def save(self):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        if self.id:
            cursor.execute("UPDATE l10n_locations SET fname=%s, lineno=%s, "
                           "msgid_id=%s, href=%s WHERE id=%s",
                           (self.fname, self.lineno, self.msgid_id,
                            self.href, self.id))
        else:
            cursor.execute("INSERT INTO l10n_locations "
                           "(msgid_id, fname, lineno, href) VALUES "
                           "(%s, %s, %s, %s)",
                           (self.msgid_id, self.fname, self.lineno, self.href))
        db.commit()
        cursor.execute("SELECT id FROM l10n_locations WHERE msgid_id=%s AND "
                       "fname=%s AND lineno=%s",
                       (self.msgid_id, self.fname, self.lineno))
        row = cursor.fetchone()
        if row:
            self.id = row[0]

    def delete(self):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("DELETE FROM l10n_locations WHERE "
                       "msgid_id=%s AND fname=%s AND lineno=%s",
                       (self.msgid_id, self.fname, self.lineno))
        db.commit()



class Translation(object):
    locale_id = None
    msgid_id = None
    string = None
    idx = 0
    flags = ''
    uc = ''
    ts = None
    sid = None
    status = 'waiting'

    def __init__(self, env, locale_id, msgid_id, string='', idx=0, sid=''):
        assert locale_id is not None
        assert msgid_id is not None
        self.env = env
        self.locale_id = locale_id
        self.msgid_id = msgid_id
        self.string = string
        self.idx = idx
        self.sid = sid
        self.ts = int(time.time())
        self.refresh()

    def refresh(self):
        #print 'refreshing translation -> locale_id: %s  msgid_id: %s' % (self.locale_id, self.msgid_id)
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT string, flags, uc, sid, status, ts FROM "
                       "l10n_translations WHERE locale_id=%s AND msgid_id=%s "
                       "AND idx=%s", (self.locale_id, self.msgid_id, self.idx))
        row = cursor.fetchone()
        if row:
            self.string, self.flags, self.uc, self.sid, self.status, self.ts = row
            self.flags = self.flags.split(',')
            self.uc = self.uc.split('\n')
            return True
        return False

    def update_stats(self):
        locale = LocaleCatalog.get_by_id(self.env, self.locale_id)
        locale.update_stats()

    def save(self):
        assert self.locale_id is not None
        assert self.msgid_id is not None
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("UPDATE l10n_translations SET idx=%s, string=%s, "
                       "flags=%s, uc=%s, sid=%s, status=%s, ts=%s WHERE "
                       "locale_id=%s AND msgid_id=%s",
                       (self.idx, self.string, ','.join(self.flags), '\n'.join(self.uc),
                        self.sid, self.status, int(time.time()), self.locale_id,
                        self.msgid_id))
        if not cursor.rowcount:
            cursor.execute("INSERT INTO l10n_translations (locale_id, msgid_id,"
                           " idx, string, flags, uc, sid, status, ts) VALUES ("
                           "%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                           (self.locale_id, self.msgid_id, self.idx,
                            self.string, ','.join(self.flags),
                            '\n'.join(self.uc), self.sid, self.status,
                            int(time.time())))
        db.commit()
        self.refresh()

    def delete(self):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("DELETE FROM l10n_translations WHERE "
                       "locale_id=%s AND msgid_id=%s",
                       (self.locale_id, self.msgid_id))
        db.commit()

    @property
    def locations(self):
        msgid = Message.get_by_id(self.env, self.msgid_id)
        return msgid.locations

