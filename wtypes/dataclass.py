"""Compatability for wtyped dataclasses."""
import builtins
import dataclasses

import jsonschema

import wtypes


class Setter:
    def __setattr__(self, key, object):
        """Only test the attribute being set to avoid invalid state."""
        for k in (key, ""):
            if key in self.__annotations__:
                cls = self.__annotations__[key]
                break

        else:
            return builtins.object.__setattr__(self, key, object)

        if hasattr(cls, "validate"):
            cls.validate(object)
        else:
            wtypes.validate_generic(object, cls)

        builtins.object.__setattr__(self, key, object)


class DataClass(Setter, wtypes.Trait, wtypes.base._Object):
    """Validating dataclass type
    
Examples
--------

    >>> class q(DataClass): a: int
    >>> q._schema.toDict()
    {'type': 'object', 'properties': {'a': {'type': 'integer'}}, 'required': ['a']}

    >>> q(a=10)
    q(a=10)
    
    >>> assert not isinstance({}, q)
    
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
        dataclasses.dataclass(cls)
        required = []
        for key in cls.__annotations__:
            if not hasattr(cls, key):
                required.append(key)
        if required:
            cls._schema["required"] = list(
                set(cls._schema.get("required", []) + required)
            )
