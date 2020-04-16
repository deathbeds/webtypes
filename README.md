A extended trait and type system for python using `jsonschema`. 

`wtypes` is an extended type and trait system for python.

* [Documentation](https://wtypes.readthedocs.io/)
* [Pypi](https://pypi.org/project/wtypes/)
* [Tests](https://github.com/deathbeds/wtypes/actions)


```bash
pip install wtypes
```

        from wtypes import *
        
<!--

        import pydantic, traitlets, IPython, jupyter, genson, hypothesis_jsonschema, hypothesis, dataclasses

-->

`wtypes` provide:
* Extended type system python validation that feature a `jsonschema` and symbollic type composition.
    
        Integer, Float, Dict, List, Email, Uri, Color, Datetime, Regex
        
* Configurable `dataclasses`.

        class Thing(DataClass):
            name: String
            location: Uri|Jsonpointer

        class Thing(DataClass):
            name: String
            location: Uri|Jsonpointer
            
        Thing(name='wtypes', location='https://github.com/deathbeds/wtypes')

* Typed evented objects.

        class Thing(evented.DataClass):
            name: String
            location: Uri|Jsonpointer
            
        Thing(name='wtypes', location='https://github.com/deathbeds/wtypes')


* Generate examples of types with [`hypothesis_jsonschema`][hyposchema] and [`genson`][genson]

        Uri.example(), Datetime.example(), Dict[{'a': Email}].example()

* Mixed python and `jsonschema` types

        t = Instance[range] | Integer
        t(10), t(range(10))
        
* _future work_ will expand on semantic RDF type information.

## Background

`wtypes` is inspired by `traitlets` - the core trait library used by `IPython` and `jupyter` - and
`pydantic` -  a `jsonschema` type system for python. Both `pydantic and traitlets` build type systems that can be validated. `pydantic` lacks interactive validate, a feature of `traitlets`. `traitlets` also provides an observable pattern for evented objects. Both `pydantic and traitlets` types are represented as python `object`s. `wtypes` includes features from these libraries in a composable `type` system. 

[pydantic]: https://pydantic-docs.helpmanual.io/usage/settings/
[traitlets]: https://traitlets.readthedocs.io/en/stable/
[ipython]: https://ipython.readthedocs.io/
[hyposchema]: https://github.com/Zac-HD/hypothesis-jsonschema
[genson]: https://pypi.org/project/genson/
[dataclasses]: https://docs.python.org/3/library/dataclasses.html
[wtypes]: https://github.com/deathbeds/wtypes
