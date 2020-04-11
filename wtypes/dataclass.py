"""Compatability for wtyped dataclasses."""
import wtypes, dataclasses, jsonschema
class DataClass(wtypes.wtypes.Trait, wtypes.wtypes._Object):
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
        self = super(Trait, cls).__new__(cls)
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
            jsonschema.validate(
                object,
                self._schema.get("properties", {}).get(key, {}),
                format_checker=jsonschema.draft7_format_checker,
            )
            if key in properties
            else jsonschema.validate(
                {key: object},
                {**self._schema, "required": []},
                format_checker=jsonschema.draft7_format_checker,
            )
        )
        super().__setattr__(key, object)
