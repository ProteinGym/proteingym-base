from abc import ABC, abstractmethod


class LookupField(ABC):
    """The abstract base class for lookup fields.

    Descriptor for a dataclass field to enable lazy loading of data from external
    resources.
    """

    identifier: str = ""

    @abstractmethod
    def resolve(self, id_: str) -> dict[str, str]:
        """Method to resolve data.

        Implement this method to query data from the intended resource.

        Returns:
            all data in form mapping of strings
        """

    def __init__(self, default: str | None = None):
        self.default = default

    def __set_name__(self, owner, name):
        if self.identifier == name:
            raise ValueError("Look up identifier must not be a LookupField")
        self.private_name = "_" + name

    def __get__(self, obj, type_=None) -> str:
        if (
            # no lookup if value already available
            obj.__dict__.get(self.private_name, None) is None
            # no lookup if the db identifier is not defined
            and getattr(obj, self.identifier) is not None
        ):
            data = self.resolve(getattr(obj, self.identifier))
            obj.__dict__.update(
                {
                    f"_{k}": v
                    for k, v in data.items()
                    if obj.__dict__.get(f"_{k}", None) is None
                }
            )

        return obj.__dict__.get(self.private_name)

    def __set__(self, obj, value: str) -> None:
        if value is self:
            value = self.default
        obj.__dict__[self.private_name] = value
