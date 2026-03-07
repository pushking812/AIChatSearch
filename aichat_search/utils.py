# aichat_search/utils.py

from datetime import datetime


def parse_datetime(iso_str: str) -> datetime:
    if not iso_str:
        return None

    iso_str = iso_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(iso_str)

    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)

    return dt
