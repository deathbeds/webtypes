"""Evented wtypes, the observable pattern


.. Observable pattern:
.. Traits observe:

"""

import contextlib
import functools
import inspect
import typing

import wtypes


class spec:
    @wtypes.specification
    def dlink(this, source, that, target, callable):
        """"""

    @wtypes.specification
    def link(this, source, that, target):
        """"""


def get_jawn(thing, key, object):
    if isinstance(thing, typing.Mapping):
        return thing.get(key, object)
    return getattr(thing, key, object)


def set_jawn(thing, key, object):
    if isinstance(thing, typing.Mapping):
        thing[key] = object
    else:
        setattr(thing, key, object)


class spec_impl:
    def __enter__(self):
        wtypes.manager.register(type(self))

    def __exit__(self, *e):
        wtypes.manager.unregister(type(self))


class wtypes_impl(spec_impl):
    @wtypes.implementation
    def dlink(this, source, that, target, callable):
        if (
            isinstance(target, str)
            and hasattr(that, target)
            or isinstance(that, typing.Mapping)
            and target in that
        ):
            set_jawn(that, target, get_jawn(this, source, None))
        if issubclass(type(this), wtypes.Trait):
            if issubclass(type(that), wtypes.Trait):
                this._registered_links = this._registered_links or {}
                this._registered_id = this._registered_id or {}
                this._registered_links[source] = this._registered_links.get(source, {})
                if id(that) not in this._registered_links[source]:
                    this._registered_links[source][id(that)] = {}
                if target not in this._registered_links[source][id(that)]:
                    this._registered_links[source][id(that)][target] = []
                if id(that) not in this._registered_id:
                    this._registered_id[id(that)] = that
                if callable not in this._registered_links[source][id(that)][target]:
                    this._registered_links[source][id(that)][target].append(callable)
                return this

            elif isinstance(that, wtypes.python_types.Forward["ipywidgets.Widget"]):
                this.observe(source, lambda x: setattr(that, target, x["new"]))
            elif isinstance(
                that, wtypes.python_types.Forward["param.parameterized.Parameterized"]
            ):
                this.observe(source, lambda x: setattr(that, target, x["new"]))

        elif isinstance(this, wtypes.python_types.Forward["ipywidgets.Widget"]):
            this.observe(lambda x: that.__setitem__(target, x["new"]), source)
        elif isinstance(
            this, wtypes.python_types.Forward["param.parameterized.Parameterized"]
        ):

            def param_wrap(param, that, target):
                def callback(*events):
                    for event in events:
                        set_jawn(that, target, event.new)

            this.param.watch(param_wrap(this, that, target), source)


wtypes.manager.add_hookspecs(spec)
wtypes.manager.register(wtypes_impl)


class Link:
    _registered_parents = None
    _registered_links = None
    _registered_id = None
    _deferred_changed = None
    _deferred_prior = None
    _depth = 0
    _display_id = None

    def __enter__(self):
        self._depth += 1

    def __exit__(self, *e):
        self._depth -= 1
        if not self._depth:
            self._propagate()
            self._update_display()

    def link(this, source, that, target):
        wtypes.manager.hook.dlink(
            this=this, source=source, that=that, target=target, callable=None
        )
        wtypes.manager.hook.dlink(
            this=that, source=target, that=this, target=source, callable=None
        )
        return this

    def dlink(self, source, that, target, callable=None):
        """
        
    Examples
    --------
        >>> class d(Dict): a: int
        >>> e, f = d(a=1), d(a=1)
        >>> e.dlink('a', f, 'a', lambda x: 2*x)
        {'a': 1}
        >>> e['a'] = 7
        >>> f
        {'a': 14}

        """

        wtypes.manager.hook.dlink(
            this=self, source=source, that=that, target=target, callable=callable
        )
        return self

    def observe(self, source="", callable=None):
        """The callable has to define a signature."""
        return self.dlink(source, self, source, callable=callable)

    def _propagate(self, *changed, **prior):
        self._deferred_changed = list(self._deferred_changed or changed)
        self._deferred_prior = {**prior, **(self._deferred_prior or {})}

        if self._depth == 0:
            while self._deferred_changed:
                key = self._deferred_changed.pop(-1)
                old = (self._deferred_prior or {}).pop(key, None)
                for hash in (
                    self._registered_links[key]
                    if self._registered_links and key in self._registered_links
                    else []
                ):
                    thing = self._registered_id[hash]
                    for k, v in self._registered_links[key][hash].items():
                        if k == key and hash == id(self):
                            for func in v:
                                func(
                                    dict(
                                        new=self.get(key, None)
                                        if hasattr(self, "get")
                                        else None,
                                        old=old,
                                        object=self,
                                        name=key,
                                    )
                                )
                        else:
                            for to, functions in self._registered_links[key][
                                hash
                            ].items():
                                if functions:
                                    function = functions[-1]
                                    if callable(function):
                                        thing.update({to: function(self[key])})
                                    else:
                                        if get_jawn(thing, to, None) is not get_jawn(
                                            self, key, inspect._empty
                                        ):
                                            set_jawn(
                                                thing, to, get_jawn(self, key, None)
                                            )

    def _update_display(self):
        if self._display_id:
            import IPython, json

            data, metadata = self._repr_mimebundle_(None, None)
            self._display_id.update(data, metadata=metadata, raw=True)

        for parent in self._registered_parents or []:
            parent._update_display()

    def _ipython_display_(self):
        import IPython, json

        shell = IPython.get_ipython()
        data, metadata = self._repr_mimebundle_(None, None)
        if self._display_id:
            self._display_id.display(data, metadata=metadata, raw=True)
        else:
            self._display_id = IPython.display.display(data, raw=True, display_id=True)

    def _repr_mimebundle_(self, include=None, exclude=None):
        return {"text/plain": str(self)}, {}


class _EventedObject(Link):
    ...


class _EventedDict(_EventedObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._link_parent(self)

    def _link_parent(self, object):
        for k, v in object.items():
            if isinstance(v, Link):
                v._registered_parents = v._registered_parents or []
                self in v._registered_parents or v._registered_parents.append(self)

    def __setitem__(self, key, object):
        with self:
            prior = self.get(key, None)
            super().__setitem__(key, object)
            self._link_parent({key: object})
            if object is not prior:
                self._propagate(key, **{key: prior})

    def update(self, *args, **kwargs):
        with self:
            args = dict(*args, **kwargs)
            prior = {x: self[x] for x in args if x in self}
            super().update(args)
            self._link_parent(args)
            prior = {
                k: v for k, v in prior.items() if v is not self.get(k, inspect._empty)
            }
            self._propagate(*args, **prior)


class _EventedDataClass(_EventedObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._link_parent(self)

    def _link_parent(self, object):
        for k, v in object.items():
            if isinstance(v, Link):
                v._registered_parents = v._registered_parents or []
                self in v._registered_parents or v._registered_parents.append(self)

    def __setattr__(self, key, object):
        if key in {
            "_depth",
            "_deferred_changed",
            "_deferred_prior",
            "_registered_parents",
            "_registered_links",
            "_registered_id",
            "_display_id",
        }:
            return super().__setattr__(key, object)

        with self:
            prior = getattr(self, key, None)
            super().__setattr__(key, object)
            self._link_parent({key: object})
            if object is not prior:
                self._propagate(key, **{key: prior})


class _EventedList(Link):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._link_parent(self)

    def _link_parent(self, object):
        for v in object:
            if isinstance(v, Link):
                v._registered_parents = v._registered_parents or []
                for p in v._registered_parents:
                    if p is self:
                        continue
                else:
                    v._registered_parents.append(self)

    def __exit__(self, *e):
        self._depth -= 1
        if not self._depth:
            self._update_display()
        e != (None, None, None) and self._update_display()

    def __setitem__(self, key, object):
        if isinstance(key, str):
            return
        with self:
            super().__setitem__(key, object)
            self._link_parent([object])

    def append(self, object):
        with self:
            super().append(object)
            self._link_parent([object])

    def insert(self, index, object):
        with self:
            super().insert(index, object)
            self._link_parent([object])

    def extend(self, object):
        with self:
            super().extend(object)
            self._link_parent(object)

    def pop(self, index=-1):
        with self:
            return super().pop(index)

    def observe(self, callable=None):
        """The callable has to define a signature."""
        return self.dlink("", self, "", callable=callable)


class List(_EventedList, wtypes.wtypes.List):
    ...


class Bunch(_EventedDict, wtypes.wtypes.Bunch):
    """An evented dictionary/bunch

Examples
--------

    >>> e, f = Bunch(), Bunch()
    >>> e.link('a', f, 'b')
    Bunch({})
    >>> e['a'] = 1
    >>> f.toDict()
    {'b': 1}
    >>> e.update(a=100)
    >>> f.toDict()
    {'b': 100}
    
    >>> f['b'] = 2
    >>> assert e['a'] == f['b']
    >>> e = Bunch().observe('a', print)
    >>> e['a'] = 2
    {'new': 2, 'old': None, 'object': Bunch({'a': 2}), 'name': 'a'}
    """


class Dict(_EventedDict, wtypes.wtypes.Dict):
    """An evented dictionary/bunch

Examples
--------

    >>> e, f = Dict(), Dict()
    >>> e.link('a', f, 'b')
    {}
    >>> e['a'] = 1
    >>> f
    {'b': 1}
    >>> e.update(a=100)
    >>> f
    {'b': 100}
    
    >>> f['b'] = 2
    >>> assert e['a'] == f['b']
    >>> e = Dict().observe('a', print)
    >>> e['a'] = 2
    {'new': 2, 'old': None, 'object': {'a': 2}, 'name': 'a'}
    
    """


class DataClass(_EventedDataClass, wtypes.DataClass):
    ...


class Namespace(Dict):
    """An event namespace to visualize track the annotated fields.
    
    
Examples
--------
    >>> # evented.Namespace.register()
    
    """

    def _repr_mimebundle_(self, include=None, exclude=None):
        return (
            {
                "text/plain": repr(
                    {
                        key: self.get(key, None)
                        for key in self.get("__annotations__", {})
                    }
                )
            },
            {},
        )

    @classmethod
    def register(cls):
        shell = __import__("IPython").get_ipython()
        shell.user_ns = cls(shell.user_ns)
        return shell.user_ns

    @classmethod
    def unregister(cls):
        shell = __import__("IPython").get_ipython()
        shell.user_ns = dict(shell.user_ns)
