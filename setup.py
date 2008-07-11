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
import tl10nm

setup(name=tl10nm.__package__,
      version=tl10nm.__version__,
      author=tl10nm.__author__,
      author_email=tl10nm.__email__,
      url=tl10nm.__url__,
      download_url='http://python.org/pypi/%s' % tl10nm.__package__,
      description=tl10nm.__summary__,
      long_description=tl10nm.__description__,
      license=tl10nm.__license__,
      platforms="OS Independent - Anywhere Python and Trac >=0.11 is known to run.",
      install_requires = ['Trac>0.11', 'Genshi>=0.5', 'Babel'],
      keywords = "trac plugin l10n",
      packages=find_packages(),
      package_data={
        'tl10nm': [
            'templates/*.html',
            'htdocs/css/*.css',
            'htdocs/img/*.png',
            'htdocs/js/*.js',
        ]
      },
      message_extractors = {
        'tl10nm': [
            ('**.py', 'python', None),
            ('**/templates/**.html', 'genshi', None),
            ('public/**', 'ignore', None)
        ]
      },
      entry_points = {
        'trac.plugins': [
            'tl10nm = tl10nm',
        ],
        'distutils.commands': [
            'extract = babel.messages.frontend:extract_messages',
            'init = babel.messages.frontend:init_catalog',
            'compile = babel.messages.frontend:compile_catalog',
            'update = babel.messages.frontend:update_catalog'
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
