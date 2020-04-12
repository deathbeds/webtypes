"""Evented wtypes, the observable pattern


.. Observable pattern:
.. Traits observe:

"""

import wtypes, inspect

class Link:
    _registered_links = None
    _registered_id = None
    _deferred_changed = None
    _deferred_prior = None
    _depth = 0

    def __enter__(self):
        self._depth += 1

    def __exit__(self, *e):
        self._depth -= 1
        self._deferred_changed and e == (None, None, None) and self._propagate()

    def link(this, source, that, target):
        this.dlink(source, that, target)
        that.dlink(target, this, source)
        return this

    def dlink(self, source, that, target, callable=None):
        """
        
    Examples
    --------
        >>> class d(Dict): a: int
        >>> e, f = d(a=1), d(a=1)
        >>> e.dlink('a', f, 'a', lambda x: 2*x)
        >>> e['a'] = 7
        >>> f
        {'a': 14}

        """
        if self is that and source == 'target':
            raise TypeError("""Linking types to themselves causes recursion.""")
        self._registered_links = self._registered_links or {}
        self._registered_id = self._registered_id or {}
        self._registered_links[source] = self._registered_links.get(source, {})
        if id(that) not in self._registered_links[source]:
            self._registered_links[source][id(that)] = {}
        if target not in self._registered_links[source][id(that)]:
            self._registered_links[source][id(that)][target] = None
        if id(that) not in self._registered_id:
            self._registered_id[id(that)] = that
        self._registered_links[source][id(that)][target] = callable
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
                    self._registered_links[key] if self._registered_links else []
                ):
                    thing = self._registered_id[hash]
                    if hash == id(self):
                        for func in self._registered_links[key][hash]:
                            func(
                                self,
                                dict(
                                    new=getattr(self, key, None),
                                    old=old,
                                    object=self,
                                    name=key,
                                ),
                            )
                    else:
                        for to, function in self._registered_links[key][hash].items():
                            if callable(function):
                                thing.update({to: function(self[key])})
                            else:
                                if thing.get(to, None) is not self.get(
                                    key, inspect._empty
                                ):
                                    thing.update({to: self[key]})

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
            prior and self._propagate(*prior, **prior)


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
    Bunch({'a': 2}) {'new': 2, 'old': None, 'object': Bunch({'a': 2}), 'name': 'a'}
    
    """


class Dict(_EventedDict, wtypes.wtypes.Dict):
    """An evented dictionary/bunch

Examples
--------

    >>> e, f = Dict(), Dict()
    >>> e.link('a', f, 'b')
    Dict({})
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
    Dict({'a': 2}) {'new': 2, 'old': None, 'object': Dict({'a': 2}), 'name': 'a'}
    
    """