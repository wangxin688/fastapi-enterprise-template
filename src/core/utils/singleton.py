from collections.abc import Callable
from typing import ParamSpec, TypeVar

T = TypeVar("T")
P = ParamSpec("P")


def singleton(cls: type[T]) -> Callable[..., T]:
    """
    Singleton decorator for any class implements.

    Args:
        cls (Type[T]): Class type.

    Returns:
        Callable[[P.args, P.kwargs], T]: Instance of cls with the given arguments.
    """
    _instance: dict[type[T], T] = {}

    def _singleton(*args: P.args, **kwargs: P.kwargs) -> T:
        if cls not in _instance:
            _instance[cls] = cls(*args, **kwargs)
        return _instance[cls]

    return _singleton
