from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import get_args

import httpx
import pytest

import companyenrich
from companyenrich import CompanyEnrichError
from companyenrich._common import NdjsonDecoder, backoff, build_query, retry_delay
from companyenrich.types import CompanyExpansion, PersonExpansion

SPEC = json.loads((Path(__file__).parent.parent / "openapi" / "v2.json").read_text("utf-8"))


def headers(**values: str) -> httpx.Headers:
    return httpx.Headers({key.replace("_", "-"): value for key, value in values.items()})


def test_build_query_repeats_lists_and_drops_none() -> None:
    query = {"expand": ["a", "b"], "flag": False, "on": True, "missing": None, "n": 3, "s": "x"}
    assert build_query(query) == [
        ("expand", "a"),
        ("expand", "b"),
        ("flag", "false"),
        ("on", "true"),
        ("n", "3"),
        ("s", "x"),
    ]


def test_backoff_grows_and_is_capped() -> None:
    assert 0.375 <= backoff(0) <= 0.5
    assert 0.75 <= backoff(1) <= 1.0
    assert 6.0 <= backoff(20) <= 8.0


@pytest.mark.parametrize(
    ("value", "expected"),
    [("7", 7.0), ("0", 0.0), ("-3", 0.0), ("1.5", 1.5)],
)
def test_retry_delay_honors_retry_after_seconds(value: str, expected: float) -> None:
    assert retry_delay(429, headers(retry_after=value), 0, retry_safe=False) == expected


def test_retry_delay_honors_retry_after_date() -> None:
    when = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=30), usegmt=True)
    delay = retry_delay(503, headers(retry_after=when), 0, retry_safe=True)
    assert delay is not None
    assert 25 <= delay <= 31


@pytest.mark.parametrize("value", ["soon", "nan", "inf"])
def test_retry_delay_falls_back_to_backoff_on_a_bad_header(value: str) -> None:
    delay = retry_delay(429, headers(retry_after=value), 0, retry_safe=False)
    assert delay is not None
    assert 0.375 <= delay <= 0.5


def test_retry_delay_parses_the_rate_limit_window_only_for_429() -> None:
    window = headers(x_ratelimit_window="00:01:05.5000000")
    assert retry_delay(429, window, 0, retry_safe=False) is None  # Longer than the 60s cap.
    short = headers(x_ratelimit_window="00:00:35.7551671")
    assert retry_delay(429, short, 0, retry_safe=False) == pytest.approx(35.7551671)
    delay = retry_delay(503, short, 0, retry_safe=True)
    assert delay is not None
    assert delay <= 0.5


@pytest.mark.parametrize("status", [408, 500, 502, 503, 504])
def test_retry_delay_only_repeats_ambiguous_failures_when_safe(status: int) -> None:
    assert retry_delay(status, headers(), 0, retry_safe=True) is not None
    assert retry_delay(status, headers(), 0, retry_safe=False) is None


@pytest.mark.parametrize("status", [400, 401, 402, 403, 404, 413, 422])
def test_retry_delay_never_repeats_client_errors(status: int) -> None:
    assert retry_delay(status, headers(), 0, retry_safe=True) is None


def test_ndjson_decoder_handles_chunk_boundaries() -> None:
    decoder = NdjsonDecoder()
    payload = '{"domain":"café.com"}\n{"domain":"b.com"}\r\n\n{"domain":"c.com"}'.encode()
    split = payload.index(0xC3) + 1
    records = decoder.feed(payload[:split]) + decoder.feed(payload[split:]) + decoder.flush()
    assert [record["domain"] for record in records] == ["café.com", "b.com", "c.com"]


def test_ndjson_decoder_keeps_unicode_line_separators_inside_strings() -> None:
    line = '{"description":"one\u2028two\u0085three"}\n'.encode()
    assert NdjsonDecoder().feed(line) == [{"description": "one\u2028two\u0085three"}]


def test_ndjson_decoder_reports_malformed_records() -> None:
    with pytest.raises(CompanyEnrichError, match="invalid NDJSON"):
        NdjsonDecoder().feed(b"not json\n")


def test_ndjson_flush_is_empty_after_a_trailing_newline() -> None:
    decoder = NdjsonDecoder()
    assert decoder.feed(b'{"a":1}\n') == [{"a": 1}]
    assert decoder.flush() == []


def test_expansion_literals_match_the_spec() -> None:
    schemas = SPEC["components"]["schemas"]
    company = schemas["CompanySearchV2Request"]["properties"]["expand"]["items"]["enum"]
    person = schemas["PersonSearchV2Request"]["properties"]["expand"]["items"]["enum"]
    assert sorted(get_args(CompanyExpansion)) == sorted(company)
    assert sorted(get_args(PersonExpansion)) == sorted(person)


def test_types_module_imports_at_runtime() -> None:
    import companyenrich.types as types

    assert all(hasattr(types, name) for name in types.__all__)


def test_public_exports_exist() -> None:
    assert all(hasattr(companyenrich, name) for name in companyenrich.__all__)
