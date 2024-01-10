import re
from typing import TypeVar
from unicodedata import normalize

_T = TypeVar("_T", str, int, float)

_pruntutaion_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')


MAC_ADDRESS_LENGTH = 12


def mac_address_validator(mac: str) -> str:
    _mac_address_re = r"^[0-9a-fA-F]{12}$"
    input_mac = re.sub(r"[^0-9a-fA-F]", "", mac)
    if len(mac) != MAC_ADDRESS_LENGTH:
        raise ValueError("validation_error.bad_mac_format")
    if re.match(_mac_address_re, input_mac):
        return ":".join(input_mac[i : i + 2] for i in range(0, len(input_mac), 2)).lower()
    raise ValueError("validation_error.bad_mac_format")


def items_to_list(values: _T | list[_T]) -> list[_T]:
    if isinstance(values, int | str | float):
        return [values]
    return values


def slugify(text: str, delim: str | None = "-") -> str:
    result = []
    for word in _pruntutaion_re.split(text.lower()):
        normallize_word = normalize("NFKD", word).encode("ascii", "ignore").decode("utf-8")
        if normallize_word:
            result.append(normallize_word)
    return delim.join(result)
