# Generated from the _async package by scripts/unasync.py. Do not edit.

from __future__ import annotations

from typing import TYPE_CHECKING

from .._common import ApiRequest, RequestOptions
from ._http import HTTPClient

if TYPE_CHECKING:
    from ..types import AutocompleteResponse, IndustryList


class Industries:
    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    def list(self, *, options: RequestOptions | None = None) -> IndustryList:
        """Lists all industries and their NAICS code prefixes. Free."""
        return self._http.request(ApiRequest("GET", "/v2/industries", options=options))


class Autocomplete:
    """Suggests up to 10 values for a search filter, ordered by popularity. Free."""

    def __init__(self, http: HTTPClient, path: str) -> None:
        self._http = http
        self._path = path

    def autocomplete(
        self, query: str, *, options: RequestOptions | None = None
    ) -> AutocompleteResponse:
        return self._http.request(
            ApiRequest("GET", self._path, query={"query": query}, options=options)
        )
