"""GitHub GraphQL API client for retrieving contribution calendars."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

GRAPHQL_ENDPOINT = "https://api.github.com/graphql"
DEFAULT_TIMEOUT_SECONDS = 30


def execute_graphql(
    token: str,
    query: str,
    variables: Dict[str, Any],
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """Executes a GraphQL query against the GitHub API with authentication and error handling."""
    if not token or not token.strip():
        raise ValueError("GitHub access token is required and cannot be empty")

    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        GRAPHQL_ENDPOINT,
        data=payload,
        headers={
            "Authorization": f"Bearer {token.strip()}",
            "Content-Type": "application/json",
            "User-Agent": "leozaow-streak-stats-engine",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status_code = response.getcode()
            response_data = json.load(response)
    except urllib.error.HTTPError as e:
        status_code = e.code
        err_body = e.read().decode("utf-8", errors="replace")
        if status_code == 401:
            raise PermissionError("GitHub API authentication failed: 401 Unauthorized") from e
        if status_code == 403:
            raise PermissionError(f"GitHub API access forbidden (403): rate limit or scope issue. {err_body}") from e
        if status_code == 429:
            raise RuntimeError("GitHub API rate limit exceeded (429)") from e
        raise RuntimeError(f"GitHub API HTTP error {status_code}: {err_body}") from e
    except urllib.error.URLError as e:
        raise ConnectionError(f"Failed to connect to GitHub API: {e.reason}") from e

    if not isinstance(response_data, dict):
        raise ValueError("Malformed GitHub API response: expected JSON object")

    if response_data.get("errors"):
        errs = response_data["errors"]
        raise RuntimeError(f"GitHub GraphQL query errors: {json.dumps(errs, ensure_ascii=False)}")

    data = response_data.get("data")
    if data is None:
        raise ValueError("GitHub API returned empty data object")

    return data


def fetch_account_created_at(token: str, username: str) -> date:
    """Retrieves the creation date of the specified GitHub account."""
    query = """
    query($login: String!) {
      user(login: $login) {
        createdAt
      }
    }
    """
    data = execute_graphql(token, query, {"login": username})
    user = data.get("user")
    if not user:
        raise ValueError(f"GitHub user '{username}' was not found.")

    created_iso = user.get("createdAt")
    if not created_iso:
        raise ValueError(f"User '{username}' payload missing createdAt field.")

    return datetime.fromisoformat(created_iso.replace("Z", "+00:00")).date()


def fetch_contributions_chunk(
    token: str,
    username: str,
    start_date: date,
    end_date: date,
) -> Tuple[Dict[date, int], int]:
    """Retrieves contribution days for a single window (up to 365 days) via GraphQL.

    Returns:
        (days_dict, total_contributions_in_window)
    """
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
                contributionLevel
              }
            }
          }
        }
      }
    }
    """
    from_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    to_dt = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

    variables = {
        "login": username,
        "from": from_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": to_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    data = execute_graphql(token, query, variables)
    user = data.get("user")
    if not user:
        raise ValueError(f"User '{username}' not found in contributions query.")

    coll = user.get("contributionsCollection", {})
    calendar = coll.get("contributionCalendar", {})
    total_in_window = int(calendar.get("totalContributions", 0))

    days: Dict[date, int] = {}
    weeks = calendar.get("weeks", [])
    for week in weeks:
        for day in week.get("contributionDays", []):
            d_str = day.get("date")
            c_count = day.get("contributionCount", 0)
            if d_str:
                d = date.fromisoformat(d_str)
                if start_date <= d <= end_date:
                    days[d] = int(c_count)

    return days, total_in_window


def fetch_all_contributions(
    token: str,
    username: str,
    created_at: date,
    reference_date: date,
) -> Tuple[Dict[date, int], int]:
    """Retrieves all historical contributions in consecutive 365-day chunks.

    Returns:
        (all_days_dict, rolling_year_total)
    """
    all_days: Dict[date, int] = {}
    rolling_year_total = 0

    cursor = created_at
    while cursor <= reference_date:
        chunk_end = min(cursor + timedelta(days=364), reference_date)
        chunk_days, chunk_total = fetch_contributions_chunk(token, username, cursor, chunk_end)
        all_days.update(chunk_days)

        # The last chunk reaching reference_date gives the freshest total
        if chunk_end == reference_date:
            rolling_year_total = chunk_total

        cursor = chunk_end + timedelta(days=1)

    return all_days, rolling_year_total
