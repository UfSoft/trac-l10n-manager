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


from babel.messages.plurals import PLURALS

class Catalog(object):
    id = None
    plurals = 1
    def __init__(self, env, locale='', repobase='', fpath='', revision=''):
        self.env = env
        self.locale = locale
        self.fpath = fpath
        self.revision = revision
        self.repobase = repobase
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT id,plurals FROM l10n_catalogs WHERE locale=%s "
                       "AND fpath=%s AND revision=%s AND repobase=%s",
                       (self.locale, self.fpath, self.revision, self.repobase))
        row = cursor.fetchone()
        if row:
            self.id, self.plurals = row
        else:
            if locale in PLURALS:
                self.plurals = PLURALS[locale][0]
            elif '_' in locale:
                loc = locale.split('_')[0]
                if loc in PLURALS:
                    self.plurals = PLURALS[loc][0]

    def save(self):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        if not self.id:
            cursor.execute("INSERT INTO l10n_catalogs "
                           "(locale, repobase, fpath, plurals, revision) "
                           " VALUES (%s, %s, %s, %s, %s)",
                           (self.locale, self.repobase, self.fpath,
                            self.plurals, self.revision))
        else:
            cursor.execute("UPDATE l10n_catalogs SET locale=%s, repobase=%s "
                           "fpath=%s, revision=%s WHERE id=%s",
                           (self.locale, self.repobase, self.fpath,
                            self.revision, self.id))
        db.commit()
        cursor.execute("SELECT id FROM l10n_catalogs WHERE locale=%s AND "
                       "fpath=%s AND revision=%s AND repobase=%s",
                       (self.locale, self.fpath, self.revision, self.repobase))
        row = cursor.fetchone()
        if row:
            self.id = row[0]

    def messages(self):
        if not self.id:
            return []
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT DISTINCT msgid FROM l10n_messages INNER JOIN "
                       "l10n_locations ON (l10n_locations.msgid_id=l10n_messages.id) "
                       "WHERE locale_id=%s ORDER BY l10n_locations.fname,"
                       "l10n_locations.lineno,l10n_messages.msgid ", (self.id,))
        rows = cursor.fetchall()
        messages = []
        for row in rows:
            msgid = row[0]
            msg = Message(self.env, self.id, msgid)
            messages.append(msg)

        return messages
    messages = property(messages)

    def delete(self):
        for msg in self.messages:
            msg.delete()
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("DELETE FROM l10n_catalogs WHERE id=%s", (self.id,))
        db.commit()

    @classmethod
    def get_by_id(cls, env, id):
        db = env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT locale, repobase, fpath, revision FROM "
                       "l10n_catalogs WHERE id=%s", (id,))
        row = cursor.fetchone()
        if not row:
            return None
        return Catalog(env, *row)

    @classmethod
    def get_all(cls, env, locale=None, no_empty_locale=False):
        db = env.get_db_cnx()
        cursor = db.cursor()
        sql = "SELECT locale, repobase, fpath, revision FROM l10n_catalogs"
        if locale:
            sql += " WHERE locale=%s"
            cursor.execute(sql, (locale,))
        elif no_empty_locale and not locale:
            sql += " WHERE locale!=''"
            cursor.execute(sql)
        else:
            cursor.execute(sql)
        catalogs = []
        for locale, repobase, fpath, revision in cursor:
            catalogs.append(Catalog(env, locale, repobase, fpath, revision))
        return catalogs

class Message(object):
    id = None
    msgid = None
    plural = None
    flags = ''
    ac = ''
    uc = ''
    previous_id = ''
    lineno = ''
    context = ''

    def __init__(self, env, locale_id, msgid):
        self.env = env
        self.locale_id = locale_id
        self.msgid = msgid

        db = env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT id,plural,flags,ac,uc,previous_id,lineno,context"
                       " FROM l10n_messages WHERE locale_id=%s AND msgid=%s",
                       (locale_id, msgid))
        row = cursor.fetchone()
        if row:
            self.id, self.plural, self.flags, self.ac, self.uc, \
                self.previous_id, self.lineno, self.context = row
            self.flags = self.flags.split(',')


    def save(self):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
#        print list(self.flags)
        print self.__dict__
        print 2, ','.join(self.flags), '\n'.join(self.ac), '\n'.join(self.uc), \
                        self.previous_id, self.lineno, self.context, \
                        self.msgid, self.locale_id
        cursor.execute("UPDATE l10n_messages SET plural=%s, flags=%s, ac=%s, uc=%s,"
                       "previous_id=%s, lineno=%s, context=%s WHERE msgid=%s AND locale_id=%s",
                       (self.plural, ','.join(list(self.flags)), '\n'.join(self.ac), '\n'.join(self.uc),
                        '\n'.join(self.previous_id), self.lineno, self.context,
                        self.msgid, self.locale_id))
        if not cursor.rowcount:
            print 1
            cursor.execute("INSERT INTO l10n_messages (locale_id,msgid,plural,"
                           "flags,ac,uc,previous_id,lineno,context) VALUES (%s,%s,"
                           "%s,%s,%s,%s,%s,%s,%s)",
                           (self.locale_id, self.msgid, self.plural, ','.join(self.flags),
                            '\n'.join(self.ac), '\n'.join(self.uc), '\n'.join(self.previous_id), self.lineno,
                            self.context))
        db.commit()
        cursor.execute("SELECT id FROM l10n_messages WHERE msgid=%s AND "
                       "locale_id=%s", (self.msgid, self.locale_id))
        row = cursor.fetchone()
        if row:
            self.id = row[0]

    def delete(self):
        for location in self.locations:
            location.delete()
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("DELETE FROM l10n_messages WHERE "
                       "locale_id=%s AND msgid=%s",
                       (self.locale_id, self.msgid))
        db.commit()

    def locations(self):
        if not self.id:
            self.save()
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT msgid_id, fname, lineno from l10n_locations WHERE "
                       "msgid_id=%s ORDER BY fname, lineno", (self.id,))
        rows = cursor.fetchall()
        locs = []
        for row in rows:
            location = Location(self.env, *row)
            locs.append(location)
#            locs.append(tuple(row))
#        print 999, locs
        return locs
    locations = property(locations)


class Location(object):
#    locale_id = None
#    msgid = None
    id = None
    msgid_id = None
    fname = None
    lineno = None
    href = None

    def __init__(self, env, msgid_id, fname=None, lineno=None):
        self.env = env
#        self.locale_id = locale_id
        self.msgid_id = msgid_id
        self.fname = fname
        self.lineno = lineno
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT id, href FROM l10n_locations WHERE msgid_id=%s AND "
                       "fname=%s AND lineno=%s",
                       (self.msgid_id, self.fname, self.lineno))
#        rows = cursor.fetchall()
        row = cursor.fetchone()
#        self.locs = []
#        for row in rows:
#            self.locs.append(tuple(row))
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
#        if not cursor.rowcount:
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





