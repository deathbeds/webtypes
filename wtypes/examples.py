import wtypes


def generate_strategy_from_object(*object):
    import genson

    builder = genson.SchemaBuilder()
    for object in object:
        if isinstance(object, type):
            builder.add_schema(wtypes.base._get_schema_from_typeish(object))
        else:
            builder.add_object(object)

    schema = builder.to_schema()
    return wtypes.wtypes.Trait.create("Generated", **schema)


def generate_strategy_from_type(type):
    """Generate a hypothesis strategy from a type. 
        
        
    Note
    ----
    Requires hypothesis_jsonschema
    """
    return __import__("hypothesis_jsonschema").from_schema(
        wtypes.base._get_schema_from_typeish(type)
    )


def generate_example(type):
    return type(generate_strategy_from_type(type).example())


wtypes.base._SchemaMeta.example = generate_example
