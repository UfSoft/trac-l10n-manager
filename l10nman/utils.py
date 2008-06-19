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

from babel import localedata
from babel.core import Locale

AVAILABLE_LOCALES = {}

def _build_locales():
    locales = map(Locale.parse, localedata.list())
    for locale in locales:
        if str(locale) not in AVAILABLE_LOCALES:
            AVAILABLE_LOCALES[str(locale)] = (
                str(locale), locale.english_name, locale.display_name)

_build_locales()
