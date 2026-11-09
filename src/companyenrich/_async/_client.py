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
from ._batches import AsyncBatches
from ._companies import AsyncCompanies
from ._geo import AsyncGeo
from ._http import AsyncHTTPClient
from ._people import AsyncPeople
from ._reference import AsyncAutocomplete, AsyncIndustries

if TYPE_CHECKING:
    from ..types import CurrentUser


class AsyncCompanyEnrich:
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
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._http = AsyncHTTPClient(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
            http_client=http_client,
        )
        self.companies = AsyncCompanies(self._http)
        self.people = AsyncPeople(self._http)
        self.batches = AsyncBatches(self._http)
        self.geo = AsyncGeo(self._http)
        self.industries = AsyncIndustries(self._http)
        self.keywords = AsyncAutocomplete(self._http, "/v2/keywords/autocomplete")
        self.technologies = AsyncAutocomplete(self._http, "/v2/technologies/autocomplete")
        self.positions = AsyncAutocomplete(self._http, "/v2/positions/autocomplete")

    async def me(self, *, options: RequestOptions | None = None) -> CurrentUser:
        """Returns the authenticated user, including credit balance and plan capabilities. Free."""
        return await self._http.request(ApiRequest("GET", "/v2/me", options=options))

    async def close(self) -> None:
        """Releases network connections."""
        await self._http.close()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()
