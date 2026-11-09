"""Logic shared by the sync and async clients. Nothing in this module performs I/O."""

from __future__ import annotations

import json
import math
import os
import random
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from functools import lru_cache
from importlib import metadata
from typing import Any, Literal, TypedDict

import httpx

from ._errors import CompanyEnrichError

DEFAULT_BASE_URL = "https://api.companyenrich.com"
DEFAULT_TIMEOUT = 120.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_POLL_INTERVAL = 2.0

_BASE_BACKOFF = 0.5
_MAX_BACKOFF = 8.0
_MAX_SERVER_REQUESTED_WAIT = 60.0
_RETRYABLE_STATUSES = frozenset({408, 500, 502, 503, 504})
_TIMESPAN = re.compile(r"^(\d+):(\d{2}):(\d{2}(?:\.\d+)?)$")


class RequestOptions(TypedDict, total=False):
    """Overrides for a single request."""

    #: Timeout in seconds. ``None`` disables it.
    timeout: float | None
    max_retries: int
    headers: Mapping[str, str]


@dataclass(frozen=True)
class ApiRequest:
    method: Literal["GET", "POST"]
    path: str
    query: Mapping[str, Any] | None = None
    body: Any = None
    #: Whether the request can be repeated after an ambiguous failure, such as a dropped
    #: connection or a 5xx response, without risking a double charge or a duplicate batch.
    #: Defaults to true for GET and false for POST.
    retry_safe: bool | None = None
    options: RequestOptions | None = None

    @property
    def can_retry_ambiguous_failure(self) -> bool:
        return self.method == "GET" if self.retry_safe is None else self.retry_safe


@lru_cache(maxsize=1)
def sdk_version() -> str:
    try:
        return metadata.version("companyenrich")
    except metadata.PackageNotFoundError:
        return "0.0.0"


def resolve_api_key(api_key: str | None) -> str:
    resolved = api_key if api_key is not None else os.environ.get("COMPANYENRICH_API_KEY")
    if not resolved:
        raise CompanyEnrichError(
            "Missing API key. Pass `api_key` or set the COMPANYENRICH_API_KEY environment variable."
        )
    return resolved


def compact(values: Mapping[str, Any]) -> dict[str, Any]:
    """Drops unset arguments so they are not sent to the API."""
    return {key: value for key, value in values.items() if value is not None}


def build_query(query: Mapping[str, Any] | None) -> list[tuple[str, Any]]:
    params: list[tuple[str, Any]] = []
    for key, value in (query or {}).items():
        if value is None:
            continue
        if isinstance(value, Sequence) and not isinstance(value, str):
            params.extend((key, _query_value(item)) for item in value)
        else:
            params.append((key, _query_value(value)))
    return params


def _query_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def build_headers(
    api_key: str,
    accept: str,
    default_headers: Mapping[str, str] | None,
    options: RequestOptions,
) -> httpx.Headers:
    headers = httpx.Headers(
        {
            "Accept": accept,
            "Authorization": f"Bearer {api_key}",
            "User-Agent": f"companyenrich-python/{sdk_version()}",
        }
    )
    headers.update(default_headers or {})
    headers.update(options.get("headers") or {})
    return headers


def retry_delay(
    status: int, headers: httpx.Headers, attempt: int, retry_safe: bool
) -> float | None:
    """Returns how long to wait before retrying, or ``None`` if the request must not be retried."""
    # A 429 is rejected before any work happens, so it is safe to repeat for every request.
    if status != 429 and not (retry_safe and status in _RETRYABLE_STATUSES):
        return None

    requested = _parse_retry_after(headers.get("retry-after"))
    if requested is None and status == 429:
        requested = _parse_timespan(headers.get("x-ratelimit-window"))
    if requested is None:
        return backoff(attempt)
    return requested if requested <= _MAX_SERVER_REQUESTED_WAIT else None


def backoff(attempt: int) -> float:
    ceiling: float = min(_MAX_BACKOFF, _BASE_BACKOFF * 2**attempt)
    return ceiling * (0.75 + random.random() * 0.25)


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        seconds = float(value)
    except ValueError:
        pass
    else:
        return max(0.0, seconds) if math.isfinite(seconds) else None
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())


def _parse_timespan(value: str | None) -> float | None:
    """Parses a .NET TimeSpan such as ``00:00:35.7551671`` into seconds."""
    match = _TIMESPAN.match(value or "")
    if match is None:
        return None
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def parse_json(content: bytes, status: int) -> Any:
    if not content:
        return None
    try:
        return json.loads(content)
    except ValueError as error:
        raise CompanyEnrichError(
            f"The API returned an invalid JSON response (status {status})"
        ) from error


def parse_error_body(response: httpx.Response) -> Any:
    try:
        return json.loads(response.content)
    except ValueError:
        return response.text


class NdjsonDecoder:
    """Splits a byte stream into JSON records.

    Lines are split on bytes rather than with ``str.splitlines``, which would also break on
    characters such as U+2028 that are valid inside a JSON string.
    """

    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, chunk: bytes) -> list[Any]:
        self._buffer += chunk
        *lines, rest = self._buffer.split(b"\n")
        self._buffer = rest
        return [_parse_line(line) for line in lines if line.strip()]

    def flush(self) -> list[Any]:
        rest, self._buffer = self._buffer, bytearray()
        return [_parse_line(rest)] if rest.strip() else []


def _parse_line(line: bytes | bytearray) -> Any:
    try:
        return json.loads(line)
    except ValueError as error:
        raise CompanyEnrichError("The API returned an invalid NDJSON record") from error
