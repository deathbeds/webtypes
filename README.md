A trait-like type system for python using jsonschema. Inspired by a `traitlets`.

```bash
pip install wtypes
```


`wtypes` is an extended type and trait system for python.

* [Documentation](https://wtypes.readthedocs.io/)
* [Pypi](https://pypi.org/project/wtypes/)
* [Tests](https://github.com/deathbeds/wtypes/actions)

`wtypes` provides:
* Extended type system validation with `jsonschema`
* Configurable objects.
* Evented objects.
* Semantic RDF type information.


    import wtypes as w
    class a(w.Dict):
        i: w.Integer = 20
        user: w.Email