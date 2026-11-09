from __future__ import annotations

from typing import TYPE_CHECKING

from .._common import ApiRequest, RequestOptions
from ._http import AsyncHTTPClient

if TYPE_CHECKING:
    from ..types import AutocompleteResponse, IndustryList


class AsyncIndustries:
    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    async def list(self, *, options: RequestOptions | None = None) -> IndustryList:
        """Lists all industries and their NAICS code prefixes. Free."""
        return await self._http.request(ApiRequest("GET", "/v2/industries", options=options))


class AsyncAutocomplete:
    """Suggests up to 10 values for a search filter, ordered by popularity. Free."""

    def __init__(self, http: AsyncHTTPClient, path: str) -> None:
        self._http = http
        self._path = path

    async def autocomplete(
        self, query: str, *, options: RequestOptions | None = None
    ) -> AutocompleteResponse:
        return await self._http.request(
            ApiRequest("GET", self._path, query={"query": query}, options=options)
        )
