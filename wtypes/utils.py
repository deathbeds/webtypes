import dataclasses
import typing

import jsonschema
import munch

import wtypes


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


def validate_schema(object: object, schema: dict) -> None:
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
                    validate_generic(thing, target)

        validate = {
            **validate,
            "properties": {
                **validate["properties"],
                **{x: {} for x in validate["properties"]},
            },
        }
    if "items" in validate:
        items = getattr(schema, "__annotations__", {}).get("", validate["items"])
        if isinstance(object, list):
            [validate_generic(x, items) for x in object]
        validate = {**validate, "items": {}}

    jsonschema.validate(
        object, validate, format_checker=jsonschema.draft7_format_checker
    )


def validate_generic(object, cls):
    if cls is None:
        return
    if isinstance(cls, dict):
        validate_schema(object, cls)
        return
    if isinstance(cls, tuple):
        cls = typing.Union[cls]
    if isinstance(cls, typing._GenericAlias):
        if cls.__origin__ is typing.Union:
            for args in cls.__args__:
                if isinstance(object, args):
                    break
            else:
                raise wtypes.ValidationError(f"{object} is not an instance of {cls}")
        else:
            if cls.__origin__ is tuple:
                for i, value in enumerate(object):
                    if not validate_generic(value, cls.__args__[i]):
                        raise wtypes.ValidationError(
                            f"Element {i}: {object} is not an instance of {cls.__args__[i]}"
                        )
            elif cls.__origin__ is list:
                for i, value in enumerate(object):
                    if not validate_generic(value, cls.__args__[0]):
                        raise wtypes.ValidationError(
                            f"Element {i}: {object} is not an instance of {cls.__args__[0]}"
                        )
            elif object.__origin__ is dict:
                for key, value in object.items():
                    if not validate_generic(value, cls.__args__[1]):
                        raise wtypes.ValidationError(
                            f"Entry {key}: {object} is not an instance of {cls.__args__[0]}"
                        )
        return True

    if isinstance(cls, type) and not isinstance(object, cls):
        raise wtypes.ValidationError(
            f"{object} is not an instance of {getattr(cls, '_schema', cls)}."
        )
    return True
