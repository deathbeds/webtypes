import abc
import dataclasses
import typing

import jsonschema

import wtypes


class ValidateMeta(abc.ABCMeta):
    def validate(self, object, schema):
        if schema is None:
            return
        if isinstance(schema, dict):
            if dataclasses.is_dataclass(object):
                return self.validate_dataclasses(object, schema)
            if "properties" in schema and schema["properties"]:
                return self.validate_schema_object(object, schema)
            if "items" in schema and schema["items"]:
                if isinstance(schema["items"], dict):
                    return self.validate_schema_array(object, schema)
                return self.validate_schema_array(object, schema)
            return self.validate_schema(object, schema)
        if isinstance(schema, typing._GenericAlias):
            return self.validate_generic(object, schema)
        if isinstance(schema, (tuple, type)):
            return self.validate_type(object, schema)

    def validate_generic(self, object, schema):
        if schema.__origin__ is typing.Union:
            return self.validate_generic_union(object, schema)
        if schema.__origin__ is tuple:
            return self.validate_generic_tuple(object, schema)
        if schema.__origin__ in (set, list):
            return self.validate_generic_list(object, schema)
        if schema.__origin__ is dict:
            return self.validate_generic_dict(object, schema)

    def validate_generic_union(self, object, schema):
        for args in schema.__args__:
            try:
                self.validate(object, args)
                break
            except:
                ...
        else:
            raise wtypes.ValidationError(f"{object} is not an instance of {schema}")

    def validate_generic_tuple(self, object, schema):
        for i, value in enumerate(object):
            if i < len(schema.__args__):
                self.validate(value, schema.__args__[i])

    def validate_generic_dict(self, object, schema):
        for key, value in object.items():
            self.validate(value, cls.__args__[1])

    def validate_generic_list(self, object, schema):
        for i, value in enumerate(object):
            self.validate(value, schema.__args__[0])

    def validate_type(self, object, schema):
        if not isinstance(object, schema):
            raise jsonschema.ValidationError(f"{object} is not of type {schema}")

    def validate_schema(self, object, schema):
        jsonschema.validate(
            object, schema, format_checker=jsonschema.draft7_format_checker
        )

    def validate_schema_object(self, object, schema):
        annotations = getattr(object, "__annotations__", {})
        for property in list(schema["properties"]):
            if property in annotations or "" in annotations:
                target = object.__annotations__.get(
                    property, object.__annotations__.get("")
                )
                if isinstance(object, typing.Mapping) and property in object:
                    thing = object[property]
                elif hasattr(object, property):
                    thing = getattr(object, property)
                else:
                    continue

                self.validate(thing, target)
                schema = {
                    **schema,
                    "properties": {
                        **schema["properties"],
                        **{x: {} for x in schema["properties"]},
                    },
                }

        self.validate_schema(object, schema)

    def validate_schema_array(self, object, schema):
        self.validate_schema(object, schema)

    def validate_dataclasses(self, object, schema):
        self.validate(vars(object), schema)


class Validate(metaclass=ValidateMeta):
    ...
