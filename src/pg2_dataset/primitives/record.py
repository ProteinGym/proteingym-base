class Record:
    def __init__(self, base=None, **kwargs):
        super().__init__()

        # Internal storage and other attributes
        self._store = {}
        self._features = None
        self._targets = None

        # Initialize from a base record if provided
        if base and isinstance(base, type(self)):
            self._store = base._store.copy()

        # Initialize from a dict if provided
        elif base and isinstance(base, dict):
            self._store = base.copy()

        # Update with provided kwargs
        self._store.update(kwargs)

    def __getattr__(self, key):
        if key.startswith("__") and key.endswith("__"):
            raise AttributeError
        if key in self._store:
            return self._store[key]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")

    def __setattr__(self, key, value):
        if key.startswith("_") or key in dir(self.__class__):
            super().__setattr__(key, value)
        else:
            self._store[key] = value

    def __getitem__(self, key):
        return self._store[key]

    def __setitem__(self, key, value):
        self._store[key] = value

    def __delitem__(self, key):
        del self._store[key]

    def __contains__(self, key):
        return key in self._store

    def __len__(self):
        return len([k for k in self._store if not k.startswith("pg2_")])

    def __repr__(self):
        d = {k: v for k, v in self._store.items()}
        return f"Record({d})" + f" (features={self._features})" + f" (targets={self._targets})"

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return isinstance(other, Record) and self._store == other._store

    def __hash__(self):
        return hash(tuple(self._store.items()))

    def keys(self):
        return [k for k in self._store.keys() if not k.startswith("pg2_")]

    def values(self):
        return [v for k, v in self._store.items() if not k.startswith("pg2_")]

    def items(self):
        return [(k, v) for k, v in self._store.items() if not k.startswith("pg2_")]

    def get(self, key, default=None):
        return self._store.get(key, default)

    def with_features(self, *keys):
        self._features = set(keys)
        return self

    def with_targets(self, *keys):
        self._targets = set(keys)
        return self

    def __iter__(self):
        return iter(dict(self._store))

    def copy(self, **kwargs):
        return type(self)(base=self, **kwargs)
