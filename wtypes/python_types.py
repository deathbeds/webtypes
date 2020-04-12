import sys
import typing

import wtypes


class _ForwardSchema(wtypes.base._StringSchema):
    def __getitem__(cls, object):
        if not isinstance(object, tuple):
            object = (object,)
        schema = []
        for object in object:
            cls = cls.create(cls.__name__)
            if isinstance(object, str):
                schema.append(typing.ForwardRef(object))
            else:
                schema.append(typing.ForwardRef(cls.__name__))
                schema[-1].__forward_evaluated__ = True
                schema[-1].__forward_value__ = object

        cls._schema = typing.Union[tuple(schema)]
        return cls

    def validate(cls, object):
        cls._schema._evaluate(sys.modules, sys.modules)
        return True

    def eval(cls):
        if hasattr(cls._schema, "__args__"):
            return tuple(x.eval() for x in cls._schema.__args__)
        return cls._schema._evaluate(sys.modules, sys.modules)


class Forward(wtypes.Trait, metaclass=_ForwardSchema):
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
        return super().__new__(cls)(*args, **kwargs)

    @classmethod
    def validate(cls, object):
        if not isinstance(object, cls.eval()):
            raise ValueError(f"{object} is not an instance of {cls.eval()}.")
