from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

from companyenrich import AsyncCompanyEnrich
from tests.helpers import Recorder


def client_with(
    responses: Sequence[httpx.Response | Exception], **options: Any
) -> tuple[AsyncCompanyEnrich, Recorder]:
    recorder = Recorder(responses)
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(recorder))
    return AsyncCompanyEnrich("test-key", http_client=http_client, **options), recorder
