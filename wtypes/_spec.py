import pluggy

specification = pluggy.HookspecMarker("wtypes")
implementation = pluggy.HookimplMarker("wtypes")
manager = pluggy.PluginManager("wtypes")


class spec:
    @specification(firstresult=True)
    def validate_type(type):
        "A hook to validate types."

    @specification(firstresult=True)
    def validate_object(object, schema):
        "A hook to validate types."


manager.add_hookspecs(spec)
del pluggy
