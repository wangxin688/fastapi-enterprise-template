from src._types import P, T


def singleton(cls: T) -> T:
    """Singleton decorator for any class implements."""
    _instance = {}

    def _singleton(*args: P.args, **kwargs: P.kwargs) -> T:
        if cls not in _instance:
            _instance[cls] = cls(*args, **kwargs)
        return _instance[cls]

    return _singleton
