"""Normalize Telegram usernames for matching external forms."""


def normalize_handle(raw: str) -> str:
    """Match form entries with or without leading @."""
    s = raw.strip()
    if s.startswith("@"):
        s = s[1:]
    return s.lower()
