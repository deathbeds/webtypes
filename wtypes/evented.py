"""Evented wtypes, the observable pattern


.. Observable pattern:
.. Traits observe:

"""

import wtypes, inspect, contextlib, functools, typing


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
        if hasattr(that, target) or isinstance(that, typing.Mapping) and target in that:
            set_jawn(that, target, get_jawn(this, source, None))
        if issubclass(type(this), wtypes.Trait):
            if this is that and source == target:
                raise TypeError("""Linking types to themselves causes recursion.""")
            this._registered_links = this._registered_links or {}
            this._registered_id = this._registered_id or {}
            this._registered_links[source] = this._registered_links.get(source, {})
            if id(that) not in this._registered_links[source]:
                this._registered_links[source][id(that)] = {}
            if target not in this._registered_links[source][id(that)]:
                this._registered_links[source][id(that)][target] = None
            if id(that) not in this._registered_id:
                this._registered_id[id(that)] = that
            this._registered_links[source][id(that)][target] = callable
            return this


wtypes.manager.add_hookspecs(spec)
wtypes.manager.register(wtypes_impl)


class Link:
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
        self._deferred_changed and e == (None, None, None) and self._propagate()

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

    def observe(self, source, callable=None):
        """The callable has to define a signature."""
        self._registered_links = self._registered_links or {}
        self._registered_id = self._registered_id or {}
        self._registered_links[source] = self._registered_links.get(source, {})
        if id(self) not in self._registered_links[source]:
            self._registered_links[source][id(self)] = []
        if id(self) not in self._registered_id:
            self._registered_id[id(self)] = self
        self._registered_links[source][id(self)].append(callable)
        return self

    def _propagate(self, *changed, **prior):
        self._deferred_changed = list(self._deferred_changed or changed)
        self._deferred_prior = {**prior, **(self._deferred_prior or {})}

        if self._depth > 0:
            return
        with self:
            while self._deferred_changed:
                key = self._deferred_changed.pop(-1)
                old = self._deferred_prior.pop(key, None)
                for hash in (
                    self._registered_links[key]
                    if self._registered_links and key in self._registered_links
                    else []
                ):
                    thing = self._registered_id[hash]
                    if hash == id(self):
                        for func in self._registered_links[key][hash]:
                            func(
                                dict(
                                    new=self.get(key, None),
                                    old=old,
                                    object=self,
                                    name=key,
                                )
                            )
                    else:
                        for to, function in self._registered_links[key][hash].items():
                            if callable(function):
                                thing.update({to: function(self[key])})
                            else:
                                if get_jawn(thing, to, None) is not get_jawn(
                                    self, key, inspect._empty
                                ):
                                    set_jawn(thing, to, self[key])
        if self._display_id:
            import IPython, json

            data, metadata = self._repr_mimebundle_(None, None)
            self._display_id.update(data, metadata=metadata, raw=True)

    def _repr_mimebundle_(self, include=None, exclude=None):
        import json

        return {"text/plain": repr(self)}, {}

    def _ipython_display_(self):
        import IPython, json

        shell = IPython.get_ipython()
        data, metadata = self._repr_mimebundle_(None, None)
        if self._display_id:
            self._display_id.display(data, metadata=metadata, raw=True)
        else:
            self._display_id = IPython.display.display(data, raw=True, display_id=True)


class _EventedDict(Link):
    def __setitem__(self, key, object):
        with self:
            prior = self.get(key, None)
            super().__setitem__(key, object)
            if object is not prior:
                self._propagate(key, **{key: prior})

    def update(self, *args, **kwargs):
        with self:
            args = dict(*args, **kwargs)
            prior = {x: self[x] for x in args if x in self}
            super().update(args)
            prior = {
                k: v for k, v in prior.items() if v is not self.get(k, inspect._empty)
            }
            for k in args:
                self._propagate(k, **prior)


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
    >>> f.toDict()
    {'b': 1}
    >>> e.update(a=100)
    >>> f.toDict()
    {'b': 100}
    
    >>> f['b'] = 2
    >>> assert e['a'] == f['b']
    >>> e = Dict().observe('a', print)
    >>> e['a'] = 2
    {'new': 2, 'old': None, 'object': Dict({'a': 2}), 'name': 'a'}
    
    """


class ipywidgets(spec_impl):
    @wtypes.implementation
    def dlink(this, source, that, target, callable):
        import ipywidgets

        if isinstance(that, ipywidgets.Widget):
            this.observe(source, lambda x: setattr(that, target, x["new"]))
            that.observe(lambda x: this.__setitem__(source, x["new"]), target)

        if isinstance(this, ipywidgets.Widget):
            this.observe(lambda x: that.__setitem__(target, x["new"]), source)
            that.observe(target, lambda x: setattr(this, source, x["new"]))


class panel(spec_impl):
    """Not working yet."""

    @wtypes.implementation
    def dlink(this, source, that, target, callable):
        def param_wrap(param, that, target):
            def callback(*events):
                for event in events:
                    set_jawn(that, target, event.new)

        import param

        if isinstance(that, param.parameterized.Parameterized):
            this.observe(source, lambda x: setattr(that, target, x["new"]))
            that.param.watch(param_wrap(that, this, source), target)

        if isinstance(this, param.parameterized.Parameterized):
            this.param.watch(param_wrap(this, that, target), source)
            that.observe(target, lambda x: setattr(this, source, x["new"]))


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
