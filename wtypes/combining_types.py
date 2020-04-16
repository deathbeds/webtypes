import typing

import wtypes


class _NotType(wtypes.base._ConstType):
    def validate(cls, object):
        super().validate(object)
        try:
            cls._type and not wtypes.validate_generic(object, cls._type)
            raise wtypes.ValidationError(f"{object} is an instance of {cls._type}")
        except wtypes.ValidationError:
            ...

    def __getitem__(cls, object):
        if isinstance(object, tuple):
            object = typing.Union[object]
        return type(
            cls.__name__ + getattr(object, "__name__", ""),
            (cls,),
            dict(),
            **{"not": wtypes.base._get_schema_from_typeish(object)},
        )


class Not(wtypes.base.Trait, metaclass=_NotType):
    """not schema.
    

Examples
--------
    
    >>> assert Not[wtypes.String](100) == 100   
    >>> assert not isinstance('abc', Not[wtypes.String])
    
Note
----
See the __neg__ method for symbollic not composition.

.. Not
    https://json-schema.org/understanding-json-schema/reference/combining.html#not
"""


class _AnyOfType(wtypes.base._ConstType):
    def validate(cls, object):
        try:
            super().validate(object)
        except ValidationError as error:
            wtypes.validate_generic(object, cls._type)

    def __getitem__(cls, object):
        if isinstance(object, tuple):
            object = typing.Union[object]
        return type(
            cls.__name__ + getattr(object, "__name__", ""),
            (cls,),
            dict(),
            py=object,
            **wtypes.base._get_schema_from_typeish(object),
        )


class AnyOf(wtypes.base.Trait, metaclass=_AnyOfType):
    """anyOf combined schema.
    
Examples
--------

    >>> assert AnyOf[wtypes.Integer, wtypes.String]('abc')
    >>> assert isinstance(10, AnyOf[wtypes.Integer, wtypes.String])
    >>> assert not isinstance([], AnyOf[wtypes.Integer, wtypes.String])
    
.. anyOf
    https://json-schema.org/understanding-json-schema/reference/combining.html#anyof
"""


class _AllOfType(wtypes.base._ConstType):
    def validate(cls, object):
        super().validate(object)
        [
            wtypes.validate_generic(object, t)
            for t in (
                cls._type.__args__
                if isinstance(cls._type, typing._GenericAlias)
                else (cls._type,)
            )
        ]

    def __getitem__(cls, object):
        if isinstance(object, tuple):
            object = typing.Union[object]
        return type(
            cls.__name__ + getattr(object, "__name__", ""),
            (cls,),
            dict(),
            py=object,
            **wtypes.base._get_schema_from_typeish(object, "allOf"),
        )


class AllOf(wtypes.base.Trait, metaclass=_AllOfType):
    """allOf combined schema.
    
Examples
--------

    >>> assert AllOf[wtypes.Float>0, wtypes.Integer/3](9)
    >>> assert isinstance(9, AllOf[wtypes.Float>0, wtypes.Integer/3])
    >>> assert not isinstance(-9, AllOf[wtypes.Float>0, wtypes.Integer/3])
    
.. allOf
    https://json-schema.org/understanding-json-schema/reference/combining.html#allof
"""


class _OneOfType(wtypes.base._ConstType):
    def validate(cls, object):
        success = 0
        for t in (
            cls._type.__args__
            if isinstance(cls._type, typing._GenericAlias)
            else (cls._type,)
        ):
            try:
                wtypes.validate_generic(object, t)
                success += 1
                if success > 1:
                    break
            except wtypes.ValidationError:
                ...
        else:
            try:
                wtypes.validate_generic(object, cls._schema)
                if success:
                    raise wtypes.ValidationError(
                        f"{object} matched too many types of {cls}"
                    )
            except wtypes.ValidationError:
                ...
        if success == 1:
            return
        elif success == 0:
            raise wtypes.ValidationError(f"{object} didn't match {cls}")
        else:
            raise wtypes.ValidationError(
                f"{object} found more than one instance of {cls}"
            )

    def __getitem__(cls, object):
        if not isinstance(object, tuple):
            object = (object,)
        return type(
            cls.__name__ + getattr(object, "__name__", ""),
            (cls,),
            dict(),
            py=typing.Union[object],
            **{"oneOf": list(map(wtypes.base._get_schema_from_typeish, object))},
        )


class OneOf(wtypes.base.Trait, metaclass=_OneOfType):
    """oneOf combined schema.

Examples
--------

    >>> assert OneOf[wtypes.Float>0, wtypes.Integer/3](-9)
    >>> assert isinstance(-9, OneOf[wtypes.Float>0, wtypes.Integer/3])
    >>> assert not isinstance(9, OneOf[wtypes.Float>0, wtypes.Integer/3])

    
.. oneOf
    https://json-schema.org/understanding-json-schema/reference/combining.html#oneof
"""
