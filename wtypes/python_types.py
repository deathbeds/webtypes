import sys
import typing

import wtypes


class _ForwardSchema(wtypes.base._ContextMeta):
    """A forward reference to an object, the object must exist in sys.modules.
    
    
Notes
-----
Python types live on the __annotations__ attribute.

    """

    _schema = None
    _schema_args = None
    _schema_kwargs = None

    def __new__(cls, name, base, kwargs, **schema):
        if "args" in schema:
            kwargs.update({"_schema_args": schema.pop("args")})
        if "keywords" in schema:
            kwargs.update({"_schema_kwargs": schema.pop("keywords")})
        kwargs["_schema"] = schema
        cls = super().__new__(cls, name, base, kwargs)
        cls._merge_schema()
        return cls

    def __add__(cls, object):
        """Add types together"""
        return type(cls.__name__, (cls, object), {})

    def _merge_schema(cls):
        types, args, kwargs = [], [], {}
        for object in reversed(cls.__mro__):
            if hasattr(object, "_schema_args"):
                args.extend(list(object._schema_args or []))
            if hasattr(object, "_schema_kwargs"):
                kwargs.update(object._schema_kwargs or {})
            if hasattr(object, "_schema"):
                if not object._schema:
                    continue
                if isinstance(object._schema, dict):
                    continue
                types.append(object._schema)

        cls._schema = types and types[0] or None
        cls._schema_args = args or None
        cls._schema_kwargs = kwargs or None

    def __getitem__(cls, object):
        if not isinstance(object, tuple):
            object = (object,)
        schema = []
        for object in object:
            if isinstance(object, str):
                schema.append(typing.ForwardRef(object))
            else:
                schema.append(typing.ForwardRef(cls.__name__))
                schema[-1].__forward_evaluated__ = True
                schema[-1].__forward_value__ = object
        cls = cls.create(cls.__name__)
        cls._schema = schema[0]
        return cls

    def validate(cls, object):
        cls.eval()

    def eval(cls):
        if hasattr(cls._schema, "__args__"):
            return tuple(x for x in cls._schema.__args__)
        return cls._schema._evaluate(sys.modules, sys.modules)


class _ArgumentSchema(_ForwardSchema):
    def __getitem__(cls, object):
        if not isinstance(object, tuple):
            object = (object,)
        return cls.create(cls.__name__, **{cls.__name__.lower(): object})


class Args(wtypes.base._NoInit, wtypes.base._NoTitle, metaclass=_ArgumentSchema):
    ...


class Keywords(wtypes.base._NoInit, wtypes.base._NoTitle, metaclass=_ArgumentSchema):
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
        args = tuple(cls._schema_args or tuple()) + args
        kwargs = {**(cls._schema_kwargs or dict()), **kwargs}
        return super().__new__(cls)(*args, **kwargs)

    @classmethod
    def validate(cls, object):
        try:
            if isinstance(object, cls.eval()):
                return
        except:
            ...
        raise wtypes.ValidationError(f"{object} is not an instance of {cls._schema}.")
