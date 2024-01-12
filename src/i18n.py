from pathlib import Path

from babel.support import Translations

from src.config import PROJECT_DIR

TRANSTIONS = {
    "zh_CN": Translations.load(Path(f"{PROJECT_DIR}/locales"), locales=["zh_CN"]),
    "en_US": Translations.load(Path(f"{PROJECT_DIR}/locales"), locales=["en_US"]),
}

translations = TRANSTIONS.get("en_US")


def set_locale(locale: str) -> None:
    global translations
    translations = TRANSTIONS.get(locale) or TRANSTIONS.get("en_US")


def _(msg: str) -> str:
    return translations.ugettext(msg)
