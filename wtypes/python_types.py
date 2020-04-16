import sys
import typing

import wtypes


class _NoType:
    ...


class _ForwardSchema(wtypes.base._ContextMeta):
    """A forward reference to an object, the object must exist in sys.modules.
    
    
Notes
-----
Python types live on the __annotations__ attribute.

    """

    _type_args = None
    _type_kwargs = None

    def __new__(cls, name, base, kwargs, **schema):
        if "args" in schema:
            kwargs.update({"_type_args": schema.pop("args")})
        if "keywords" in schema:
            kwargs.update({"_type_kwargs": schema.pop("keywords")})
        cls = super().__new__(cls, name, base, kwargs, **schema)
        cls._merge_args()
        return cls

    def __getitem__(cls, object):
        if not isinstance(object, tuple):
            object = (object,)
        schema = []
        for object in object:
            if isinstance(object, str):
                schema.append(typing.ForwardRef(object))
            else:
                schema.append(object)
        cls = cls.create(cls.__name__, py=typing.Union[tuple(schema)])
        return cls

    def validate(cls, object):
        cls.eval()

    def eval(cls):
        t = typing.Union[cls._type]
        t = t.__args__[0] if isinstance(t, typing._GenericAlias) else t
        if isinstance(t, typing.ForwardRef):
            return t._evaluate(sys.modules, sys.modules)
        return t

    def __add__(cls, object):
        # Cycle through dicts and lists
        if isinstance(object, dict):
            return type(cls.__name__ + object.__name__, (cls,), dict(), **object)
        if isinstance(object, Forward):
            return type(cls.__name__ + object.__name__, (cls, object), dict(),)
        return super().__add__(object)


class _ArgumentSchema(_ForwardSchema):
    def __getitem__(cls, object):
        if not isinstance(object, dict) and not isinstance(object, tuple):
            object = (object,)

        return type(
            cls.__name__, (cls,), {}, **{wtypes.base._lower_key(cls.__name__): object}
        )


class Args(
    _NoType, wtypes.base._NoInit, wtypes.base._NoTitle, metaclass=_ArgumentSchema
):
    ...


class Kwargs(
    _NoType, wtypes.base._NoInit, wtypes.base._NoTitle, metaclass=_ArgumentSchema
):
    ...


class Forward(metaclass=_ForwardSchema):
    """Create type using objects or forward references.

Examples
--------

    >>> assert Forward['builtins.range']() is range
    
    
    """

    def __new__(cls):
        return cls.eval()


class Class(Forward):
    """Create type using objects or forward references.

Examples
--------

    >>> assert isinstance(range, Class['builtins.range'])

    
    """

    def __new__(cls):
        object = super().__new__()
        if isinstance(object, tuple):
            object = object[0]
        return object

    @classmethod
    def validate(cls, object):
        try:
            if issubclass(object, cls.eval()):
                return
        except:
            ...
        raise wtypes.ValidationError(f"{object} is not a type of {cls._schema}.")


class Instance(Forward):
    """Create an instance of a type using objects or forward references.

Examples
--------

    >>> assert (Instance[range] + Args[10, 20])() == range(10, 20)
    >>> assert (Instance['builtins.range'] + Args[10, 20])() == range(10, 20)
    >>> assert isinstance(range(10), Instance['builtins.range'])

Deffered references.

    >>> assert not isinstance(1, Instance['pandas.DataFrame'])
    >>> assert 'pandas' not in __import__('sys').modules
    
    
    """

    def __new__(cls, *args, **kwargs):
        args = tuple(cls._type_args or tuple()) + args
        kwargs = {**(cls._type_kwargs or dict()), **kwargs}
        return cls.eval()(*args, **kwargs)

    @classmethod
    def validate(cls, object):
        wtypes.validate_generic(object, cls.eval())
