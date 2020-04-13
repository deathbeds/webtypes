import sys
import typing

import wtypes


class _ForwardSchema(wtypes.base._ContextMeta):
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

    def _merge_schema(cls):
        types, args, kwargs = [], [], {}
        for self in reversed(cls.__mro__):
            if not hasattr(self, "_schema"):
                continue
            if isinstance(self._schema, dict):
                continue
            types.append(self._schema)
            args.extend(list(self._schema_args or []))
            kwargs.update(self._schema_kwargs or {})
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
    def __new__(cls):
        return cls.eval()


class Class(Forward):
    def __new__(cls):
        object = super().__new__()
        if isinstance(object, tuple):
            object = object[0]
        return object

    @classmethod
    def validate(cls, object):
        if not issubclass(object, cls.eval()):
            raise TypeError(f"{object} is not a type of {cls.eval()}.")


class Instance(Forward):
    def __new__(cls, *args, **kwargs):
        args = (cls._schema_args or tuple()) + args
        kwargs = {**(cls._schema_kwargs or dict()), **kwargs}
        return super().__new__(cls)(*args, **kwargs)

    @classmethod
    def validate(cls, object):
        if not isinstance(object, cls.eval()):
            raise ValueError(f"{object} is not an instance of {cls.eval()}.")
