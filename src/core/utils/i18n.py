from collections import defaultdict
from collections.abc import Callable
from functools import reduce
from operator import getitem
from typing import Any, ClassVar

from src.core.utils.context import locale_ctx
from src.core.utils.singleton import singleton
from src.openapi import translations


@singleton
class I18n:
    accepted_languages: ClassVar[set[str]] = {"en_US", "zh_CN"}

    def __init__(self) -> None:
        self.translations = translations

    def gettext(self, path: str, **kwargs: Any) -> dict | str:
        locale = locale_ctx.get()
        if not locale or locale not in self.accepted_languages:
            locale = "en_US"
        founded: dict | str = self._find(locale, path)

        if len(kwargs) > 0 and isinstance(founded, str):
            try:
                return founded.format_map(defaultdict(str, **kwargs))
            except KeyError:
                return founded
        return founded

    def _find(self, language: str, path: str) -> dict | str:
        try:
            return reduce(getitem, path.split("."), self.translations[language])
        except (KeyError, TypeError):
            return f"missing translation for {language}"


_i18n: I18n = I18n()
_: Callable[..., dict | str] = _i18n.gettext
