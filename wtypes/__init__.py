#!/usr/bin/env python
# coding: utf-8

"""extended python types for the web and json

Notes
-----
Attributes
----------
simpleTypes : list
    The limited set of base types provide by jsonschema.

Todo
---
* Configuration Files
* Observable Pattern
* You have to also use ``sphinx.ext.todo`` extension

.. ``jsonschema`` documentation:
   https://json-schema.org/
"""
__version__ = "0.0.2"

import pluggy
specification = pluggy.HookspecMarker('wtypes')
implementation = pluggy.HookimplMarker('wtypes')
manager = pluggy.PluginManager('wtypes')
from . import spec
manager.add_hookspecs(spec)
del pluggy

from .base import *
from . import base
from .dataclass import *
from .string_formats import *
from . import dataclass, evented, examples

