"""Shared Plaid utilities used by both mcp_server.py and dashboard.py."""

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import plaid
from dotenv import load_dotenv
from plaid.api import plaid_api

FEED_PATH = Path(__file__).parent / "feed.json"

PLAID_ENVIRONMENTS = {
    "sandbox": plaid.Environment.Sandbox,
    "production": plaid.Environment.Production,
}


@dataclass
class FeedEntry:
    """A single MCP tool call log entry for the activity feed."""

    tool_name: str
    params: dict = field(default_factory=dict)
    result_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).strftime("%H:%M:%S"))


def get_plaid_env() -> str:
    """Return the Plaid host URL based on the PLAID_ENV setting in .env."""
    load_dotenv(override=True)
    env_name = os.environ.get("PLAID_ENV", "sandbox").lower()
    if env_name not in PLAID_ENVIRONMENTS:
        raise ValueError(f"Invalid PLAID_ENV '{env_name}'. Must be one of: sandbox, production")
    return PLAID_ENVIRONMENTS[env_name]


def get_plaid_client() -> plaid_api.PlaidApi:
    """Create and return a configured Plaid API client using credentials from .env."""
    load_dotenv(override=True)

    configuration = plaid.Configuration(
        host=get_plaid_env(),
        api_key={
            "clientId": os.environ["PLAID_CLIENT_ID"],
            "secret": os.environ["PLAID_SECRET"],
        },
    )
    api_client = plaid.ApiClient(configuration)
    return plaid_api.PlaidApi(api_client)


def load_access_tokens() -> dict[str, str]:
    """Load all ACCESS_TOKEN_* values from the .env file.

    Returns a dict mapping the label (e.g. 'CHASE') to the access token value.
    """
    load_dotenv(override=True)
    tokens: dict[str, str] = {}
    for key, value in os.environ.items():
        if key.startswith("ACCESS_TOKEN_") and value:
            label = key.removeprefix("ACCESS_TOKEN_")
            tokens[label] = value
    return tokens


def append_feed_entry(entry: FeedEntry) -> None:
    """Append a FeedEntry to feed.json, creating the file if needed."""
    entries: list[dict] = []
    if FEED_PATH.exists():
        try:
            entries = json.loads(FEED_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            entries = []

    entries.append(asdict(entry))
    FEED_PATH.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def clear_feed() -> None:
    """Reset feed.json to an empty array."""
    FEED_PATH.write_text("[]", encoding="utf-8")
