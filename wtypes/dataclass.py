"""Compatability for wtyped dataclasses."""
import builtins
import dataclasses

import jsonschema

import wtypes


class Setter:
    def __setattr__(self, key, object):
        """Only test the attribute being set to avoid invalid state."""
        type(
            "tmp",
            (wtypes.Dict,),
            {
                "__annotations__": {
                    key: self.__annotations__.get(
                        key,
                        type(
                            "tmp",
                            (wtypes.Trait,),
                            {},
                            **self._schema.get("properties", {}).get(key, {}),
                        ),
                    )
                }
            },
        ).validate({key: object})
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


# ## Configuration classes


class Configurable(DataClass):
    """A configurable classs that is create with dataclass syntax."""
