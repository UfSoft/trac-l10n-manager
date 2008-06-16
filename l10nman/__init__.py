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
# Copyright (C) 2007 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# Please view LICENSE for additional licensing information.
# =============================================================================

__version__     = '0.1.0'
__author__      = 'Pedro Algarvio'
__email__       = 'ufs@ufsoft.org'
__package__     = 'L10nManagerTracPlugin'
__license__     = 'BSD'
__url__         = 'http://hg.ufsoft.org/L10nManagerTracPlugin/'
__summary__     = 'Trac plugin to handle message catalogs'
# XXX: extend description
__description__ = 'Trac plugin to handle message catalogs'

import web_ui, admin

from trac.db import DatabaseManager
from trac.core import *
from trac.env import IEnvironmentSetupParticipant

from l10nman import db_default

class L10NManagerSetup(Component):
    implements(IEnvironmentSetupParticipant)

    # IEnvironmentSetupParticipant Methods
    def environment_created(self):
        self.found_db_version = 0
        self.upgrade_environment(self.env.get_db_cnx())

    def environment_needs_upgrade(self, db):
        cursor = db.cursor()
        cursor.execute("SELECT value FROM system WHERE name=%s",
                       (db_default.name,))
        value = cursor.fetchone()
        if not value:
            self.found_db_version = 0
            return True
        else:
            self.found_db_version = int(value[0])
            self.log.debug('L10NManager: Found db version %s, current is %s' % (
                                    self.found_db_version, db_default.version))
            return self.found_db_version < db_default.version

    def upgrade_environment(self, db):
        db_manager, _ = DatabaseManager(self.env)._get_connector()
        cursor = db.cursor()
        # Insert the default table
        old_data = {} # {table_name: (col_names, [row, ...]), ...}
        if not self.found_db_version:
            cursor.execute("INSERT INTO system (name, value) VALUES (%s, %s)",
                           (db_default.name, db_default.version))
        else:
            cursor.execute("UPDATE system SET value=%s WHERE name=%s",
                           (db_default.version, db_default.name))

            for tbl in db_default.tables:
                try:
                    cursor.execute('SELECT * FROM %s'%tbl.name)
                    old_data[tbl.name] = ([d[0] for d in cursor.description],
                                          cursor.fetchall())
                    cursor.execute('DROP TABLE %s'%tbl.name)
                except Exception, err:
                    if 'OperationalError' not in err.__class__.__name__:
                        # If it is an OperationalError, just move on to the next table
                        raise err

        for vers, migration in db_default.migrations:
            if self.found_db_version in vers:
                self.log.info('L10nManager: Running migration %s',
                              migration.__doc__)
                migration(old_data)

        for tbl in db_default.tables:
            for sql in db_manager.to_sql(tbl):
                cursor.execute(sql)

            # Try to reinsert any old data
            if tbl.name in old_data:
                data = old_data[tbl.name]
                sql = 'INSERT INTO %s (%s) VALUES (%s)' % (
                    tbl.name, ','.join(data[0]), ','.join(['%s'] * len(data[0]))
                )
                for row in data[1]:
                    try:
                        cursor.execute(sql, row)
                    except Exception, err:
                        if 'OperationalError' not in err.__class__.__name__:
                            raise
                        else:
                            self.log.debug('L10nManager: Masking exception %s',
                                           e)
