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

from trac.db import Table, Column, Index

name = 'l10n-manager'
version = 1

tables = [
    Table('l10n_catalogs', key='id')[
        Column('id', auto_increment=True),
        Column('locale'), # empty for catalog template
        Column('repobase'), # path in repo ie '/trunk/', '/branches/', etc
        Column('fpath'), # catalog file path (in repo)
        Column('revision', type="integer"), # @ catalog repo revision
        Index(['locale', 'repobase', 'fpath', 'revision'])
    ],
    Table('l10n_messages', key=('locale_id', 'msgid'))[
        Column('id', auto_increment=True),
        Column('locale_id', type="integer"), # l10n_catalogs.id
        Column('msgid'),
        # Column('msgstr'), <- diferent table, ie, user versioned translations
        # Column('locations') <- diferent table
        Column('flags'),
        Column('ac'), # auto-comments, aka, extracted comments
        Column('uc'), # user-comments
        Column('previous_id'), # previous id
        Column('lineno', type="integer"), # lineno in po(t) file
        Column('context')
    ],
    Table('l10n_locations', key=('id'))[
        Column('id', auto_increment=True),
        Column('msgid_id', type="integer"), # l10n_messages.id
        Column('fname'),
        Column('lineno', type="integer"),
        Index(['msgid_id', 'fname','lineno'])
    ]
]

migrations = []
