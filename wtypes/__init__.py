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

from .spec import *  # isort:skip
from .utils import *  # isort:skip
from .base import *  # isort:skip
from . import examples  # isort:skip
from . import base, combining_types, dataclass, python_types, utils
from .combining_types import *
from .dataclass import *
from .python_types import *
from .string_formats import *

from . import evented  # isort:skip
