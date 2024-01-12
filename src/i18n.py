from pathlib import Path

from babel.support import Translations

from src.config import PROJECT_DIR

ACCEPTED_LANGUAGES = ("zh_CN", "en_US")

TRANSITIONS = {
    "zh_CN": Translations.load(Path(f"{PROJECT_DIR}/locales"), locales=["zh_CN"]),
    "en_US": Translations.load(Path(f"{PROJECT_DIR}/locales"), locales=["en_US"]),
}

translations = TRANSITIONS.get("en_US")


def set_locale(locale: str) -> None:
    global translations  # noqa: PLW0603
    translations = TRANSITIONS.get(locale) or TRANSITIONS.get("en_US")


def _(msg: str) -> str:
    return translations.ugettext(msg)
