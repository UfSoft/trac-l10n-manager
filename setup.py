#!/usr/bin/env python
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

from setuptools import setup, find_packages
import l10nman

setup(name=l10nman.__package__,
      version=l10nman.__version__,
      author=l10nman.__author__,
      author_email=l10nman.__email__,
      url=l10nman.__url__,
      download_url='http://python.org/pypi/%s' % l10nman.__package__,
      description=l10nman.__summary__,
      long_description=l10nman.__description__,
      license=l10nman.__license__,
      platforms="OS Independent - Anywhere Python and Trac >=0.11 is known to run.",
      install_requires = ['Trac>0.11', 'Genshi>=0.5', 'Babel'],
      packages=find_packages(),
      package_data={
          'l10nman': [
              'templates/*.html',
              'htdocs/*.css',
          ]
      },
      entry_points = {
          'trac.plugins': [
              'l10nman = l10nman',
          ]
      },
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Web Environment',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: BSD License',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Topic :: Text Processing',
          'Topic :: Utilities',
          'Topic :: Internet :: WWW/HTTP',
          'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
      ]
)
