# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8

__version__     = '0.1.0'
__author__      = 'Pedro Algarvio'
__email__       = 'ufs@ufsoft.org'
__package__     = 'TracL10nManagerPlugin'
__license__     = 'BSD'
__url__         = 'http://tl10nm.ufsoft.org'
__summary__     = 'Localization Manager Trac plugin'
__description__ = """\
L10N Manager Trac Plugin
========================

 * Allows users to provide translations for managed catalogs.
 * Allow admins to download the translations in PO or MO gettext format
"""

# -------------------------- import package modules ----------------------------
import admin, resources, web_ui, perm, help, model

# -------------------- Database Init/Upgrade Code ------------------------------
from trac.core import Component, implements
from trac.env import IEnvironmentSetupParticipant
from tracext.sa import engine

class TracL10nManagerSetup(Component):
    implements(IEnvironmentSetupParticipant)
    env = log = config = None # Make pylint happier

    # IEnvironmentSetupParticipant Methods
    def environment_created(self):
        self.found_db_version = 0
        self.upgrade_environment(self.env.get_db_cnx())

    def environment_needs_upgrade(self, db):
        cursor = db.cursor()
        cursor.execute("SELECT value FROM system WHERE name=%s",
                       (model.name,))
        value = cursor.fetchone()
        if not value:
            self.found_db_version = 0
            return True
        else:
            self.found_db_version = int(value[0])
            self.log.debug("%s: Found db version %s, current is %s",
                           __package__, self.found_db_version, model.version)
            return self.found_db_version < model.version

    def upgrade_environment(self, db):
        # Currently we only create the tables, so far there's no migration done
        model.metadata.create_all(bind=engine(self.env))
        cursor = db.cursor()
        if not self.found_db_version:
            cursor.execute("INSERT INTO system (name, value) VALUES (%s, %s)",
                           (model.name, model.version))
        else:
            cursor.execute("UPDATE system SET value=%s WHERE name=%s",
                           (model.version, model.name))

