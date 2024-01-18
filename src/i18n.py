from collections import defaultdict
from collections.abc import Callable
from functools import reduce
from operator import getitem
from typing import Any, Literal, TypeAlias

from src.context import locale_ctx
from src.openapi import translations
from src.utils.singleton import singleton

ACCEPTED_LANGUAGES: TypeAlias = Literal["en_US", "zh_CN"]


@singleton
class I18n:
    def __init__(self) -> None:
        self.translations = translations

    def gettext(self, path: str, **kwargs: Any) -> dict | str:
        locale = locale_ctx.get()
        founded: dict | str = self._find(locale, path)

        if len(kwargs) > 0 and isinstance(founded, str):
            try:
                return founded.format_map(defaultdict(str, **kwargs))
            except KeyError:
                return founded
        return founded

    def _find(self, language: ACCEPTED_LANGUAGES, path: str) -> dict | str:
        try:
            return reduce(getitem, path.split("."), self.translations[language])
        except (KeyError, TypeError):
            return f"missing translation for {language}"


_i18n: I18n = I18n()
_: Callable[..., dict | str] = _i18n.gettext
