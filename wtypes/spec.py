import wtypes

@wtypes.specification(firstresult=True)
def validate_type(type):
    "A hook to validate types."

@wtypes.specification(firstresult=True)
def validate_object(object, schema):
    "A hook to validate types."