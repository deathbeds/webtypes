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

from . import base, dataclass, evented, examples, python_types
from .base import *
from .dataclass import *
from .python_types import *
from .string_formats import *

specification = pluggy.HookspecMarker("wtypes")
implementation = pluggy.HookimplMarker("wtypes")
manager = pluggy.PluginManager("wtypes")


class spec:
    @specification(firstresult=True)
    def validate_type(type):
        "A hook to validate types."

    @specification(firstresult=True)
    def validate_object(object, schema):
        "A hook to validate types."


manager.add_hookspecs(spec)
del pluggy
