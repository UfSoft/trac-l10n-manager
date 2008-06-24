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
    Table('l10n_catalogs', key='fpath')[
        Column('fpath'), # catalog template file path (in repo)
        Column('revision', type="integer"), # @ catalog repo revision
        Index(['fpath', 'revision'])
    ],
    Table('l10n_locales', key='id')[
        Column('id', auto_increment=True),
        Column('template'), # FK l10n_catalogs.fpath
        Column('locale'), # empty for catalog template
        Column('fpath'), # catalog file path (in repo)
        Column('plurals', type='integer'),
        Column('revision', type="integer"), # @ catalog repo revision
        Index(['template', 'locale', 'fpath'])
    ],
    Table('l10n_locale_stats', key='locale_id')[
        Column('locale_id', type='integer'), # FK l10n_locales.id
        Column('translated', type='integer'),
        Column('translated_percent', type='float'),
        Column('fuzzy', type='integer'),
        Column('fuzzy_percent', type='float'),
        Column('untranslated', type="integer"),
        Column('untranslated_percent', type="float")
    ],
    Table('l10n_messages', key='id')[
        Column('id', auto_increment=True),
        Column('template'), # FK l10n_catalogs.fpath
        Column('msgid'),
        Column('plural'), # plural forms
        # Column('msgstr'), <- diferent table, ie, user versioned translations
        # Column('locations') <- diferent table
        Column('flags'),
        Column('ac'), # auto-comments, aka, extracted comments
        Column('previous_id'), # previous id
        Column('lineno', type="integer"), # lineno in po(t) file
        Column('context')
    ],
    Table('l10n_locations', key=('id'))[
        Column('id', auto_increment=True),
        Column('msgid_id', type="integer"), # FK l10n_messages.id
        Column('fname'),
        Column('lineno', type="integer"),
        Column('href'),
        Index(['msgid_id', 'fname','lineno'])
    ],
    Table('l10n_translations', key=('locale_id', 'msgid_id', 'string', 'idx'))[
        Column('locale_id', type='integer'), # FK l10n_locales.id
        Column('msgid_id', type='integer'), # FK l10n_messages.id
        Column('idx', type="integer"), # plural form index, 0 for non plural
        Column('string'),
        Column('flags'),
        Column('uc'), # user-comments
        Column('sid'),
        Column('ts', type="integer"), # TimeStamp
        Column('status'), # ENUM: waiting,  reviewed, rejected, etc
        Index(['locale_id', 'msgid_id', 'string', 'idx'])
    ]
]

migrations = []
