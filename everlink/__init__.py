#!/usr/bin/env python
# encoding: utf-8
"""
__init__.py

"""
__all__ = ['everlink']

from everlink import *

# Set up the root logger

import logging
import sys
logging.basicConfig(format='%(levelname)s %(asctime)s (%(name)s): %(message)s',
                    level=logging.INFO, stream=sys.stdout, datefmt='%Y-%m-%d %H:%M:%S')
