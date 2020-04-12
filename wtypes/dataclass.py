"""Compatability for wtyped dataclasses."""
import wtypes, dataclasses, jsonschema
class DataClass(wtypes.Trait, wtypes.base._Object):
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

    def __new__(cls, *args, **kwargs):
        self = super(wtypes.Trait, cls).__new__(cls)
        # dataclass instantiates the defaults for us.
        self.__init__(*args, **kwargs)
        return self

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
        dataclasses.dataclass(cls)

    def __setattr__(self, key, object):
        """Only test the attribute being set to avoid invalid state."""
        if isinstance(object, dict):
            object = object.get(key)
        properties = self._schema.get("properties", {})
        (
            wtypes.manager.hook.validate_object(
                object=object,
                schema=self._schema.get("properties", {}).get(key, {}),
            )
            if key in properties
            else wtypes.manager.hook.validate_object(
                object={key: object},
                schema={**self._schema, "required": []},
            )
        )
        super().__setattr__(key, object)

# ## Configuration classes


class Configurable(DataClass):
    """A configurable classs that is create with dataclass syntax."""
