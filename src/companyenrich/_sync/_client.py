# Generated from the _async package by scripts/unasync.py. Do not edit.

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

import httpx
from typing_extensions import Self

from .._common import (
    DEFAULT_BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    ApiRequest,
    RequestOptions,
)
from ._batches import Batches
from ._companies import Companies
from ._geo import Geo
from ._http import HTTPClient
from ._people import People
from ._reference import Autocomplete, Industries

if TYPE_CHECKING:
    from ..types import CurrentUser


class CompanyEnrich:
    """Client for the CompanyEnrich API.

    Args:
        api_key: Defaults to the ``COMPANYENRICH_API_KEY`` environment variable.
        base_url: API origin, for proxies.
        timeout: Timeout in seconds for each attempt. ``None`` disables it.
        max_retries: How many times to retry a failed request.
        default_headers: Headers sent with every request.
        http_client: A custom ``httpx`` client. The SDK will not close it for you.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float | None = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._http = HTTPClient(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
            http_client=http_client,
        )
        self.companies = Companies(self._http)
        self.people = People(self._http)
        self.batches = Batches(self._http)
        self.geo = Geo(self._http)
        self.industries = Industries(self._http)
        self.keywords = Autocomplete(self._http, "/v2/keywords/autocomplete")
        self.technologies = Autocomplete(self._http, "/v2/technologies/autocomplete")
        self.positions = Autocomplete(self._http, "/v2/positions/autocomplete")

    def me(self, *, options: RequestOptions | None = None) -> CurrentUser:
        """Returns the authenticated user, including credit balance and plan capabilities. Free."""
        return self._http.request(ApiRequest("GET", "/v2/me", options=options))

    def close(self) -> None:
        """Releases network connections."""
        self._http.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
