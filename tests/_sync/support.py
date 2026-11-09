# Generated from the _async package by scripts/unasync.py. Do not edit.

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

from companyenrich import CompanyEnrich
from tests.helpers import Recorder


def client_with(
    responses: Sequence[httpx.Response | Exception], **options: Any
) -> tuple[CompanyEnrich, Recorder]:
    recorder = Recorder(responses)
    http_client = httpx.Client(transport=httpx.MockTransport(recorder))
    return CompanyEnrich("test-key", http_client=http_client, **options), recorder
