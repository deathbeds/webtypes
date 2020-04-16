#!/usr/bin/env python
# coding: utf-8

"""An extended type and trait system for python.

Notes
-----

Todo
---
* Widgets

.. ``jsonschema`` documentation:
   https://json-schema.org/
"""
__version__ = "0.0.1"
import abc
import builtins
import copy
import dataclasses
import functools
import inspect
import re
import typing

import jsonschema
import munch

import wtypes

ValidationError = jsonschema.ValidationError


class _Implementation:
    """An implementation of the pluggy wtypes spec.
    
Notes
-----
The implementation needs to be registered with the plugin manager.    
"""

    @wtypes.implementation
    def validate_type(type):
        jsonschema.validate(
            _get_schema_from_typeish(type),
            jsonschema.Draft7Validator.META_SCHEMA,
            format_checker=jsonschema.draft7_format_checker,
        )
        return True

    @wtypes.implementation
    def validate_object(object, schema):
        validate = munch.Munch.fromDict(schema)
        if dataclasses.is_dataclass(object):
            object = vars(object)
        if isinstance(schema, type):
            if hasattr(schema, "_schema"):
                if isinstance(schema._schema, dict):
                    validate = schema._schema
        if "properties" in validate:
            annotations = getattr(schema, "__annotations__", {})
            for property in list(validate["properties"]):
                if property in annotations or "" in annotations:
                    target = schema.__annotations__.get(
                        property, schema.__annotations__.get("")
                    )
                    if isinstance(object, typing.Mapping) and property in object:
                        thing = object[property]
                    elif hasattr(object, property):
                        thing = getattr(object, property)
                    else:
                        continue

                    if hasattr(target, "validate"):
                        target.validate(thing)
                    else:
                        wtypes.validate_generic(thing, target)

            validate = {
                **validate,
                "properties": {
                    **validate["properties"],
                    **{x: {} for x in validate["properties"]},
                },
            }
        jsonschema.validate(
            object, validate, format_checker=jsonschema.draft7_format_checker
        )
        return True


wtypes.manager.register(_Implementation)


def istype(object, cls):
    """instance(object, type) and issubclass(object, cls)
    
Examples
--------

    >>> assert istype(int, int)
    >>> assert not istype(10, int)
    
"""
    if isinstance(object, type):
        return issubclass(object, cls)
    return False


class _NoTitle:
    """A subclass suppresses the class name when combining schema"""


class _NoInit:
    """A subclass to restrict initializing an object from the type."""

    def __new__(cls, *args, **kwargs):
        raise TypeError(f"Cannot initialize the type : {cls.__name__}")


# ## `webtypes` meta schema


class _ContextMeta(abc.ABCMeta):
    """Meta operations for the context..
    
Attributes
----------
_context : dict
    The schema the object validates against.

_type : type
    The schema the object validates against.

_schema: dict

Notes
-----
A context type cannot be verified as it only describes, althrough some descriptors like SHACL can validate

"""

    _schema = None
    _context = None
    _type = None

    def __new__(cls, name, base, kwargs, **schema):

        kwargs.update(
            _schema=schema,
            _context=schema.pop("context", None),
            _type=schema.pop("py", None),
        )
        if "args" in schema:
            kwargs.update({"_type_args": schema.pop("args")})
        if "keywords" in schema:
            kwargs.update({"_type_kwargs": schema.pop("keywords")})
        cls = super().__new__(cls, name, base, kwargs)
        cls._merge_context(), cls._merge_annotations(), cls._merge_types(), cls._merge_schema(), cls._merge_args()
        if isinstance(cls._schema, dict):
            wtypes.manager.hook.validate_type(type=cls)
        return cls

    def _merge_args(cls):
        args, kwargs = [], {}
        for object in reversed(cls.__mro__):
            if hasattr(object, "_type_args"):
                if object._type_args is not None:
                    args = object._type_args
            if hasattr(object, "_type_kwargs"):
                kwargs.update(object._type_kwargs or {})
        cls._type_args = args or None
        cls._type_kwargs = kwargs or None

    def _merge_context(cls):
        context = munch.Munch()
        for self in cls.__mro__:
            context.update(munch.Munch.fromDict(getattr(self, "_context", {}) or {}))
        cls._context = context or None

    def _merge_annotations(cls):
        """Merge annotations from the module resolution order."""
        cls.__annotations__ = getattr(cls, "__annotations__", {})
        for module in reversed(type(cls).__mro__):
            cls.__annotations__.update(getattr(module, "__annotations__", {}))

    def _merge_schema(cls):
        """Merge schema from the module resolution order."""
        schema = munch.Munch()
        types = list()
        for self in reversed(cls.__mro__):
            py_types = getattr(self, "_type", None)
            for self in (py_types and (py_types,) or tuple()) + (self,):
                current = getattr(self, "_schema", {})
                if isinstance(current, dict):
                    for k, v in current.items():
                        if k in {"type", "not", "oneOf", "anyOf", "allOf", "enum"}:
                            if not (dict({k: v}) in types):
                                types.append(dict({k: v}))
                        if isinstance(v, list):
                            if k not in schema:
                                schema[k] = list()
                            schema[k] += v
                        elif isinstance(v, dict):
                            if k not in schema:
                                schema[k] = dict()
                            schema[k].update(v)
                        else:
                            schema[k] = v

        if "required" in schema:
            # Make required a unique list.
            schema["required"] = list(set(schema["required"]))
        if "properties" in schema:
            schema.properties.pop("", None)
        cls._schema = schema

    def _merge_types(cls):
        """Merge schema from the module resolution order."""
        types = []
        for self in reversed(cls.__mro__):
            current = getattr(self, "_type", None)
            if current is not None:
                types.append(current)

        if types:
            cls._type = typing.Union[tuple(types)]
        if hasattr(self, "_type_args"):
            cls._merge_args()

    def __matmul__(cls, object):
        cls = cls.create(cls.__name__)
        cls._context = cls._context or munch.Munch()
        if isinstance(object, dict):
            cls._context.update(munch.Munch.fromDict(object))
        elif isinstance(object, (str, list)):
            if not isinstance(cls._context, list):
                cls._context = [cls._context]
            if isinstance(object, str):
                cls._context = cls._context + [object]
            else:
                cls._context = cls._context + list(map(munch.Munch.fromDict, object))
            cls._context = list(filter(bool, cls._context))
        return cls

    def validate(cls, object):
        """A context type does not validate."""
        wtypes.manager.hook.validate_object(object=object, schema=cls)

    def __instancecheck__(cls, object):
        try:
            cls.validate(object)
            return True
        except:
            return False

    def create(cls, name: str, **schema):
        """Create a new schema type.
        

Parameters
----------
name: str
    The title of the new type/schema
**schema: dict
    Extra features to add include in the schema.
    
Returns
-------
type
    
        """
        return type(name, (cls,), {}, **schema)

    def __add__(cls, object):
        # Cycle through dicts and lists
        if isinstance(object, dict):
            return type(cls.__name__ + object.__name__, (cls,), dict(), **object)
        return type(
            cls.__name__ + object.__name__,
            (cls,),
            dict(),
            py=None if isinstance(object, wtypes.python_types._NoType) else object,
            **{
                "args": getattr(object, "_type_args", None),
                "keywords": getattr(object, "_type_kwargs", None),
                **getattr(object, "_schema", {}),
            },
        )

    def __neg__(cls):
        """The Not version of a type."""
        return wtypes.combining_types.Not[cls]

    def __pos__(cls):
        """The type."""
        return cls

    def __and__(cls, object):
        """AllOf the conditions"""
        return wtypes.combining_types.AllOf[cls, object]

    def __sub__(cls, object):
        """AnyOf the conditions"""
        return wtypes.combining_types.AnyOf[cls, object]

    def __or__(cls, object):
        """OneOf the conditions"""
        return wtypes.combining_types.OneOf[cls, object]


class _SchemaMeta(_ContextMeta):
    """Meta operations for wtypes.
    
The ``_SchemaMeta`` ensures that a type's extended schema is validate.
Types cannot be generated with invalid schema.

Attributes
----------
_schema : dict
    The schema the object validates against.

"""

    def __neg__(cls):
        """The Not version of a type."""
        return wtypes.combining_types.Not[cls]

    def __pos__(cls):
        """The type."""
        return cls

    def __and__(cls, object):
        """AllOf the conditions"""
        return wtypes.combining_types.AllOf[cls, object]

    def __sub__(cls, object):
        """AnyOf the conditions"""
        return wtypes.combining_types.OneOf[cls, object]

    def __or__(cls, object):
        """OneOf the conditions"""
        return wtypes.combining_types.AnyOf[cls, object]

    def validate(cls, object):
        """Validate an object against type's schema.
        
        
        
Note
----
``isinstance`` can used for validation, too.

Parameters
----------
object
    An object to validate.
        
Raises
------
jsonschema.ValidationError
    The ``jsonschema`` module validation throws an exception on failure,
    otherwise the returns a None type.
"""
        wtypes.manager.hook.validate_object(object=object, schema=cls)


class _ConstType(_SchemaMeta):
    """ConstType permits bracketed syntax for defining complex types.
            
Note
----
The bracketed notebook should differeniate actions on types versus those on objects.
"""

    def __getitem__(cls, object):
        if isinstance(object, tuple):
            object = list(object)
        return type(cls.__name__, (cls,), {}, **{_lower_key(cls.__name__): object})


class _ContainerType(_ConstType):
    """ContainerType extras schema from bracketed arguments to define complex types."""

    def __getitem__(cls, object):
        schema_key = _lower_key(cls.__name__)
        schema = munch.Munch()
        if isinstance(object, dict):
            schema.update(_get_schema_from_typeish(object))
        else:
            if isinstance(object, (list, tuple)):
                schema = [
                    value for value in map(_get_schema_from_typeish, object) if value
                ]
            else:
                schema = _get_schema_from_typeish(object)
        return cls + Trait.create(schema_key, **{schema_key: schema})


def _python_to_wtype(object):
    if isinstance(object, typing.Hashable):
        if object == str:
            object = String
        elif object == tuple:
            object = List
        elif object == list:
            object = List
        elif object == dict:
            object = Dict
        elif object == int:
            object = Integer
        elif object == tuple:
            object = Tuple
        elif object == float:
            object = Float
        elif object == builtins.object:
            object = Trait
        elif object == None:
            object = None
        elif object == bool:
            object = Bool
        elif object == set:
            object = Unique
    return object


def _get_schema_from_typeish(object, key="anyOf"):
    """infer a schema from an object."""
    if isinstance(object, typing._GenericAlias):
        # This is a typing union.
        if object.__origin__ is typing.Union:
            return munch.Munch.fromDict(
                {
                    key: list(
                        filter(bool, map(_get_schema_from_typeish, object.__args__))
                    )
                }
            )
        if object.__origin__ is tuple:
            return _get_schema_from_typeish(Tuple[object.__args__])

        if object.__origin__ is list:
            return _get_schema_from_typeish(List[object.__args__])

        if object.__origin__ is dict:
            return munch.Munch.fromDict(
                dict(additionalProperties=_get_schema_from_typeish(object.__args__[1]))
            )

    if isinstance(object, dict):
        return munch.Munch.fromDict(
            {k: _get_schema_from_typeish(v) for k, v in object.items()}
        )
    if isinstance(object, (list, tuple)):
        return list(map(_get_schema_from_typeish, object))
    object = _python_to_wtype(object)
    if isinstance(getattr(object, "_schema", None), dict):
        return object._schema
    return {}


def _lower_key(str):
    return (str[0].lower() + str[1:]).replace("-", "")


def _object_to_webtype(object):
    if isinstance(object, typing.Mapping):
        return Dict
    if isinstance(object, str):
        return String
    if isinstance(object, tuple):
        return Tuple

    if isinstance(object, typing.Sequence):
        return List
    if isinstance(object, bool):
        return Bool
    if isinstance(object, (int, float)):
        return Float
    if object == None:
        return Null
    if isinstance(object, Trait):
        return type(object)
    return Trait


def _construct_title(cls):
    if istype(cls, _NoTitle):
        return ""
    if isinstance(cls._schema, dict):
        return cls._schema.get("title", cls.__name__)
    return cls.__name__


class Trait(metaclass=_SchemaMeta):
    """A trait is an object validated by a validate ``jsonschema``.
    """

    _schema = None
    _context = None

    def __new__(cls, *args, **kwargs):
        """__new__ validates an object against the type schema and dispatches different values in return.
        
        
        
Parameters
----------
*args
    The arguments for the base object class.
**kwargs
    The keyword arguments for the base object class.
    
Returns
-------
object
    Return an instance of the object and carry along the schema information.
"""

        if dataclasses.is_dataclass(cls):
            self = super().__new__(cls)
            self.__init__(*args, **kwargs)
            cls.validate(self)
        elif isinstance(cls, _ConstType) and args:
            wtypes.validate_generic(args[0], getattr(cls, "_type", cls))
            current_type = type(args[0])
            candidate_type = _python_to_wtype(current_type)
            self = args[0]
            if candidate_type is not current_type:
                self = candidate_type(args[0])
        else:
            args = cls._resolve_defaults(*args, **kwargs)
            args and cls.validate(*args)
            self = super().__new__(cls, *args, **kwargs)
            # self.__init__(*args, **kwargs)

        return self

    @classmethod
    def _resolve_defaults(cls, *args, **kwargs) -> tuple:
        if not args and not kwargs:
            if "default" in cls._schema:
                return (cls._schema.default,)
            elif "properties" in cls._schema:
                defaults = {}
                for k, v in cls._schema["properties"].items():
                    object = get_jawn(cls, k, None)
                    if isinstance(object, dataclasses.Field):
                        if not isinstance(object.default, dataclasses._MISSING_TYPE):
                            defaults[k] = object.default
                        elif not isinstance(
                            object.default_factory, dataclasses._MISSING_TYPE
                        ):
                            defaults[k] = object.default_factory()
                    elif "default" in v:
                        defaults[k] = v["default"]

                return (defaults,)
        return args


def get_jawn(thing, key, object):
    if isinstance(thing, typing.Mapping):
        return thing.get(key, object)
    return getattr(thing, key, object)


class Description(_NoInit, Trait, _NoTitle, metaclass=_ConstType):
    """An empty type with a description
    
    
Examples
--------

    >>> yo = Description['yo']
    >>> yo._schema.toDict()
    {'description': 'yo'}

    """


class Examples(_NoInit, Trait, metaclass=_ConstType):
    """"""


class Default(_NoInit, Trait, metaclass=_ConstType):
    """"""


class Title(_NoInit, Trait, _NoTitle, metaclass=_ConstType):
    """An empty type with a title
    
    
Examples
--------

    >>> holla = Title['holla']
    >>> holla._schema.toDict()
    {'title': 'holla'}
    """


class Const(_NoInit, Trait, metaclass=_ConstType):
    """A constant
    
Examples
--------

    >>> Const[10]._schema.toDict()
    {'const': 10}
    
    
    >>> assert isinstance('thing', Const['thing'])
    >>> assert not isinstance('jawn', Const['thing']), "Because the compiler is from Philly."
    
"""


# ## Logical Types


class Bool(Trait, metaclass=_SchemaMeta, type="boolean"):
    """Boolean type
        
Examples
--------

    >>> Bool(), Bool(True), Bool(False)
    (False, True, False)
    >>> assert (Bool + Default[True])()
    
Note
----
It is not possible to base class ``bool`` so object creation is customized.
    
"""

    def __new__(cls, *args):
        args = cls._resolve_defaults(*args)
        args = args or (bool(),)
        args and cls.validate(args[0])
        return args[0]


class Null(Trait, metaclass=_SchemaMeta, type="null"):
    """nil, none, null type
        
Examples
--------

    >>> Null(None)
    >>> assert (Null + Default[None])() is None
    
.. Null Type:
    https://json-schema.org/understanding-json-schema/reference/null.html
    
"""

    def __new__(cls, *args):
        args = cls._resolve_defaults(*args)
        args and cls.validate(args[0])


# ## Numeric Types


class _NumericSchema(_SchemaMeta):
    """Meta operations for numerical types"""

    def __ge__(cls, object):
        """Inclusive minimum"""
        return cls + Minimum[object]

    def __gt__(cls, object):
        """Exclusive minimum"""
        return cls + ExclusiveMinimum[object]

    def __le__(cls, object):
        """Inclusive maximum"""
        return cls + Maximum[object]

    def __lt__(cls, object):
        """Exclusive maximum"""
        return cls + ExclusiveMaximum[object]

    __rgt__ = __lt__
    __rge__ = __le__
    __rlt__ = __gt__
    __rle__ = __ge__

    def __truediv__(cls, object):
        """multiple of a number"""
        return cls + MultipleOf[object]


class Integer(Trait, int, metaclass=_NumericSchema, type="integer"):
    """integer type
    
    
Examples
--------

    >>> assert isinstance(10, Integer)
    >>> assert not isinstance(10.1, Integer)
    >>> (Integer+Default[9])(9)
    9


    >>> bounded = (10< Integer)< 100
    >>> bounded._schema.toDict()
    {'type': 'integer', 'exclusiveMinimum': 10, 'exclusiveMaximum': 100}
    >>> assert isinstance(12, bounded)
    >>> assert not isinstance(0, bounded)
    >>> assert (Integer/3)(9) == 9
    
    """


class Float(Trait, float, metaclass=_NumericSchema, type="number"):
    """float type
    
    
    >>> assert isinstance(10, Float)
    >>> assert isinstance(10.1, Float)

Symbollic conditions.

    >>> bounded = (10< Float)< 100
    >>> bounded._schema.toDict()
    {'type': 'number', 'exclusiveMinimum': 10, 'exclusiveMaximum': 100}

    >>> assert isinstance(12.1, bounded)
    >>> assert not isinstance(0.1, bounded)

Multiples

    >>> assert (Float+MultipleOf[3])(9) == 9


.. Numeric Types:
    https://json-schema.org/understanding-json-schema/reference/numeric.html
    
    """


class MultipleOf(_NoInit, Trait, metaclass=_ConstType):
    """A multipleof constraint for numeric types."""


class Minimum(_NoInit, Trait, metaclass=_ConstType):
    """A minimum constraint for numeric types."""


class ExclusiveMinimum(_NoInit, Trait, metaclass=_ConstType):
    """A exclusive minimum constraint for numeric types."""


class Maximum(_NoInit, Trait, metaclass=_ConstType):
    """A exclusive maximum constraint for numeric types."""


class ExclusiveMaximum(_NoInit, Trait, metaclass=_ConstType):
    """A exclusive maximum constraint for numeric types."""


# ## Mapping types


class Properties(Trait, _NoInit, _NoTitle, metaclass=_ContainerType):
    """Object properties."""


class _ObjectSchema(_SchemaMeta):
    """Meta operations for the object schema."""

    def __getitem__(cls, object):
        """
        
Examples
--------
    >>> Dict[wtypes.Forward[range], int].__annotations__
    {'': typing.Union[abc.Forward, int]}
    >>> Dict[wtypes.Forward[range], int]._schema.toDict()
    {'type': 'object', 'properties': {}, 'additionalProperties': {'anyOf': [{'type': 'integer'}]}}

        
        """
        if isinstance(object, dict):
            return type(cls.__name__, (cls,), {"__annotations__": object})
        if not isinstance(object, tuple):
            object = (object,)
        return (
            type(cls.__name__, (cls,), {"__annotations__": {"": typing.Union[object]}})
            + AdditionalProperties[wtypes.AnyOf[object]]
        )


class _Object(metaclass=_ObjectSchema, type="object"):
    """Base class for validating object types."""

    def __init_subclass__(cls, **schema):
        cls._schema = munch.Munch.fromDict(cls._schema or {})
        for key, value in cls.__annotations__.items():
            cls._schema["properties"] = (
                cls._schema.get("properties", None) or munch.Munch()
            )
            cls._schema["properties"][key] = _get_schema_from_typeish(value)
            if hasattr(cls, key) and not isinstance(
                getattr(cls, key), dataclasses.Field
            ):
                cls._schema.properties[key]["default"] = getattr(cls, key)

    @classmethod
    def from_config_file(cls, *object):
        args = __import__("anyconfig").load(object)
        return cls(args)


class Dict(Trait, dict, _Object):
    """dict type
    
Examples
--------

    >>> assert istype(Dict, __import__('collections').abc.MutableMapping)
    >>> assert (Dict + Default[{'b': 'foo'}])() == {'b': 'foo'}
    >>> assert (Dict + Default[{'b': 'foo'}])({'a': 'bar'}) == {'b': 'foo', 'a': 'bar'}


    >>> assert isinstance({}, Dict)
    >>> assert not isinstance([], Dict)
    
    >>> assert isinstance({'a': 1}, Dict + Required['a',])
    >>> assert not isinstance({}, Dict + Required['a',])

    >>> assert not isinstance({'a': 'b'}, Dict[Integer, Float])
    >>> assert Dict[Integer]({'a': 1}) == {'a': 1}
    

    >>> Dict[{'a': int}]._schema.toDict()
    {'type': 'object', 'properties': {'a': {'type': 'integer'}}}
    >>> Dict[{'a': int}]({'a': 1})
    {'a': 1}

    
.. Object Type
    https://json-schema.org/understanding-json-schema/reference/object.html
    """

    def __new__(cls, *args, **kwargs):
        default = cls._resolve_defaults()
        if default:
            args = ({**default[0], **dict(*args, **kwargs)},)
        else:
            args = (dict(*args, **kwargs),)
        self = super().__new__(cls, *args)
        self.__init__(*args)
        wtypes.manager.hook.validate_object(object=self, schema=type(self))
        return self

    def __setitem__(self, key, object):
        """Only test the key being set to avoid invalid state."""
        if not self._schema.get("additionalProperties", True):
            if key not in self._schema.get("properties", {}):
                raise ValidationError(f"Additional key {key} not allowed.")
        cls = self.__annotations__.get(
            key,
            self.__annotations__.get("", self._schema.get("properties", {}).get(key)),
        )
        wtypes.validate_generic(object, cls)
        super().__setitem__(key, object)

    def update(self, *args, **kwargs):
        args = (dict(*args, **kwargs),)
        tmp = type(
            "tmp",
            (Dict,),
            {
                "__annotations__": {
                    key: self.__annotations__.get(
                        key,
                        type(
                            "tmp",
                            (Trait,),
                            {},
                            **self._schema.get("properties", {}).get(key, {}),
                        ),
                    )
                    for key in args[0]
                }
            },
        )
        wtypes.manager.hook.validate_object(object=args[0], schema=tmp)
        super().update(*args, **kwargs)


class Bunch(Dict, munch.Munch):
    """Bunch type
    
Examples
--------

    >>> Bunch[{'a': int}]._schema.toDict()
    {'type': 'object', 'properties': {'a': {'type': 'integer'}}}
    >>> Bunch[{'a': int}]({'a': 1}).toDict()
    {'a': 1}

    
.. Munch Documentation
    https://pypi.org/project/munch/
    
"""


class AdditionalProperties(Trait, _NoInit, _NoTitle, metaclass=_ContainerType):
    """Additional object properties."""


class Required(Trait, _NoInit, _NoTitle, metaclass=_ConstType):
    """Required properties."""


class minProperties(Trait, _NoInit, _NoTitle, metaclass=_ConstType):
    """Minimum number of properties."""


class maxProperties(Trait, _NoInit, _NoTitle, metaclass=_ConstType):
    """Maximum number of properties."""


class PropertyNames(Trait, _NoInit, _NoTitle, metaclass=_ConstType):
    """Propery name constraints."""


class Dependencies(Trait, _NoInit, _NoTitle, metaclass=_ConstType):
    """Properties dependencies."""


class PatternProperties(Trait, _NoInit, _NoTitle, metaclass=_ContainerType):
    """Pattern properties names."""


# ## String Type


class _StringSchema(_SchemaMeta):
    """Meta operations for strings types.
    """

    def __mod__(cls, object):
        """A pattern string type."""
        return cls + Pattern[object]

    def __gt__(cls, object):
        """Minumum string length"""
        return cls + MinLength[object]

    def __lt__(cls, object):
        """Maximum string length"""
        return cls + MaxLength[object]

    __rgt__ = __rge__ = __le__ = __lt__
    __rlt__ = __rle__ = __ge__ = __gt__


class String(Trait, str, metaclass=_StringSchema, type="string"):
    """string type.
    
    
Examples
--------

    >>> assert isinstance('abc', String)
    >>> assert (String+Default['abc'])() == 'abc'
    
String patterns

    >>> assert isinstance('abc', String%"^a")
    >>> assert not isinstance('abc', String%"^b")
    
String constraints
    
    >>> assert isinstance('abc', (2<String)<10) 
    >>> assert not isinstance('a', (2<String)<10)
    >>> assert not isinstance('a'*100, (2<String)<10)
    """


class MinLength(Trait, _NoInit, _NoTitle, metaclass=_ConstType):
    """Minimum length of a string type."""


class MaxLength(Trait, _NoInit, _NoTitle, metaclass=_ConstType):
    """Maximum length of a string type."""


class ContentMediaType(Trait, _NoInit, _NoTitle, metaclass=_ConstType):
    """Content type of a string."""


class Pattern(Trait, _NoInit, metaclass=_ConstType):
    """A regular expression pattern."""


class Format(Trait, _NoInit, _NoTitle, metaclass=_ConstType):
    ...


# ## Array Type


class _ListSchema(_SchemaMeta):
    """Meta operations for list types."""

    def __getitem__(cls, object):
        """List meta operations for bracketed type notation.


Examples
--------

    >>> List[wtypes.Forward[range], int]._type
    typing.List[typing.Union[abc.Forward, int]]

    >>> Tuple[wtypes.Forward[range], int]._type
    typing.Tuple[abc.Forward, int]

        """
        if istype(cls, Tuple):
            if not isinstance(object, tuple):
                object = (object,)
            return type(
                cls.__name__,
                (cls,),
                {},
                py=typing.Tuple[object],
                items=list(map(_get_schema_from_typeish, object)),
            )
        elif isinstance(object, tuple):
            return type(
                cls.__name__,
                (cls,),
                {},
                py=typing.List[typing.Union[object]],
                items=_get_schema_from_typeish(typing.Union[object]),
            )
        return type(
            cls.__name__,
            (cls,),
            {},
            py=typing.List[object],
            items=_get_schema_from_typeish(object),
        )

    def __gt__(cls, object):
        """Minumum array length"""
        return cls + MinItems[object]

    def __lt__(cls, object):
        """Maximum array length"""
        return cls + MaxItems[object]

    __rgt__ = __rge__ = __le__ = __lt__
    __rlt__ = __rle__ = __ge__ = __gt__


class List(Trait, list, metaclass=_ListSchema, type="array"):
    """List type
    
    
Examples
--------

List

    >>> assert isinstance([], List)
    >>> assert not isinstance({}, List)
    
Typed list

    >>> assert List[Integer]([1, 2, 3])
    >>> assert isinstance([1], List[Integer])
    >>> assert not isinstance([1.1], List[Integer])
    
    >>> List[Integer, String]._schema.toDict()
    {'type': 'array', 'items': {'anyOf': [{'type': 'integer'}, {'type': 'string'}]}}


    
Tuple        
    
    >>> assert List[Integer, String]([1, 'abc', 2])
    >>> assert isinstance([1, '1'], List[Integer, String])
    >>> assert not isinstance([1, {}], List[Integer, String])
    """

    def __new__(cls, *args, **kwargs):
        args = cls._resolve_defaults(*args) or ([],)

        if args and isinstance(args[0], tuple):
            args = (list(args[0]) + list(args[1:]),)
        args and cls.validate(args[0])
        self = super().__new__(cls, *args, **kwargs)
        return self

    def _verify_item(self, object, id=None):
        """Elemental verification for interactive type checking."""
        items = self._schema.get("items", None)
        if items or "" in self.__annotations__:
            if isinstance(items, dict):
                if isinstance(id, slice):
                    wtypes.validate_generic(object, self._type)
                else:
                    wtypes.validate_generic([object], self._type)
            elif isinstance(items, list):
                if isinstance(id, slice):
                    # condition for negative slices
                    if isinstance(self._type, typing.Generic):
                        wtypes.validate_generic(
                            object, typing.Tuple[tuple(self._type.__args__[id])]
                        )
                elif isinstance(id, int):
                    # condition for negative integers
                    if id < len(items):
                        if isinstance(self._type, typing.Generic):
                            wtypes.validate_generic(object, self._type.__args__[id])
                        else:
                            wtypes.validate_generic(object, items[id])

    def __setitem__(self, id, object):
        self._verify_item(object, id)
        prior = self[id]
        super().__setitem__(id, object)
        try:
            type(self).validate(self)
        except jsonschema.ValidationError as e:
            self[id] = prior
            raise e

    def append(self, object):
        self._verify_item(object, len(self))
        super().append(object)
        try:
            type(self).validate(self)
        except jsonschema.ValidationError as e:
            self.pop(-1)
            raise e

    def insert(self, id, object):
        self._verify_item(object, id)
        try:
            super().insert(id, object)
        except jsonschema.ValidationError as e:
            self.pop(id)
            raise e

    def extend(self, object):
        id = slice(len(self), len(self) + len(object))
        self._verify_item(object, id)
        super().extend(object)
        try:
            type(self).validate(self)
        except ValidationError as e:
            for i in range(len(object)):
                self.pop(-1)
            raise e

    def pop(self, index=-1):
        value = super().pop(index)
        try:
            type(self).validate(self)
            return value
        except ValidationError as e:
            self.insert(index, value)
            raise e


class Unique(List, uniqueItems=True):
    """Unique list type
    
    
Examples
--------

    >>> assert Unique(list('abc'))
    >>> assert isinstance([1,2], Unique)
    >>> assert not isinstance([1,1], Unique)
    
    """


class Tuple(List):
    """tuple type
    
Note
----
There are no tuples in json, they are typed lists.

    >>> assert Tuple._schema == List._schema
    
    
Examples
--------

    >>> assert isinstance([1,2], Tuple)
    >>> assert Tuple[Integer, String]([1, 'abc'])
    >>> Tuple[Integer, String]._schema.toDict()
    {'type': 'array', 'items': [{'type': 'integer'}, {'type': 'string'}]}

    >>> assert isinstance([1,'1'], Tuple[Integer, String])
    >>> assert not isinstance([1,1], Tuple[Integer, String])
    
    """


class UniqueItems(Trait, _NoInit, _NoTitle, metaclass=_ConstType):
    """Schema for unique items in a list."""


class Contains(Trait, _NoInit, _NoTitle, metaclass=_ContainerType):
    ...


class Items(Trait, _NoInit, _NoTitle, metaclass=_ContainerType):
    ...


class AdditionalItems(Trait, _NoInit, _NoTitle, metaclass=_ContainerType):
    ...


class MinItems(Trait, _NoInit, _NoTitle, metaclass=_ConstType):
    """Minimum length of an array."""


class MaxItems(Trait, _NoInit, _NoTitle, metaclass=_ConstType):
    """Maximum length of an array."""


class Enum(Trait, metaclass=_ConstType):
    """An enumerate type that is restricted to its inputs.
    
    
Examples
--------

    >>> assert Enum['cat', 'dog']('cat')
    >>> assert isinstance('cat', Enum['cat', 'dog'])
    >>> assert not isinstance('🐢', Enum['cat', 'dog'])

    
    """


class ContentEncoding(
    Enum["7bit 8bit binary quoted-printable base64".split()], _NoInit, _NoTitle
):
    """Content encodings for a string.
    
.. Json schema media:
    https://json-schema.org/understanding-json-schema/reference/non_json_data.html
"""


class If(Trait, _NoInit, _NoTitle, metaclass=_ContainerType):
    """if condition type
    
.. Conditions:
    https://json-schema.org/understanding-json-schema/reference/conditionals.html
    """


class Then(Trait, _NoInit, _NoTitle, metaclass=_ContainerType):
    """then condition type"""


class Else(Trait, _NoInit, _NoTitle, metaclass=_ContainerType):
    """else condition type"""
