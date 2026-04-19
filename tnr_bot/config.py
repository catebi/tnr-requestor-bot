"""Environment-driven settings. Extend with new env vars as features grow."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def get_environment() -> str:
    return os.getenv("ENVIRONMENT", "dev")


def get_airtable_credentials() -> tuple[str | None, str | None]:
    """Return (personal_access_token, base_id) for the current environment."""
    if get_environment() == "dev":
        return os.getenv("AIRTABLE_PAT_DEV"), os.getenv("AIRTABLE_BASE_ID_DEV")
    return os.getenv("AIRTABLE_PAT"), os.getenv("AIRTABLE_BASE_ID")
