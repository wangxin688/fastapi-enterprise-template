import io
from pathlib import Path

import pandas as pd


def bytes_to_human_readable(bytes_: int, format_string: str = "%(value).1f%(symbol)s") -> str:
    symbols = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    prefix = {}
    for i, s in enumerate(symbols[1:]):
        prefix[s] = 1 << (i + 1) * 10
    for symbol in reversed(symbols[1:]):
        if bytes_ >= prefix[symbol]:
            value = float(bytes_) / prefix[symbol]
            return format_string % locals()
    return format_string % {"symbol": symbols[0], "value": bytes_}


def export_csv(data: list[dict]) -> str:
    df = pd.DataFrame(data)
    binary_data = io.StringIO()
    df.to_csv(binary_data, index=False, encoding="utf-8")
    return binary_data.getvalue()


def get_file_size(path: str) -> str:
    return bytes_to_human_readable(Path(path).stat().st_size)


def format_duration(seconds: float) -> str:
    duration_units = [
        ("week", 60 * 60 * 24 * 7),
        ("day", 60 * 60 * 24),
        ("hour", 60 * 60),
        ("minute", 60),
        ("second", 1),
    ]

    parts = []
    for unit, duration in duration_units:
        count, seconds = divmod(int(seconds), duration)
        if count:
            parts.append(f'{count} {unit}{"s" if count > 1 else ""}')

    return ", ".join(parts) if parts else "0 seconds"
