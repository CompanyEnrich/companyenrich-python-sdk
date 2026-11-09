# Generated from the _async package by scripts/unasync.py. Do not edit.

from __future__ import annotations

from collections.abc import Generator, Sequence
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from .._common import ApiRequest, RequestOptions, compact
from ._http import HTTPClient, paginate

if TYPE_CHECKING:
    from ..types import (
        GeoCity,
        GeoCitySearchResponse,
        GeoCountry,
        GeoCountrySearchResponse,
        GeoRegions,
        GeoState,
        GeoStateSearchResponse,
    )


class Geo:
    """Geographic reference data for search filters. Every endpoint here is free."""

    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    def regions(self, *, options: RequestOptions | None = None) -> GeoRegions:
        """Lists all regions and their country codes."""
        return self._http.request(ApiRequest("GET", "/v2/geo/regions", options=options))

    def country(
        self, country_code: str, *, options: RequestOptions | None = None
    ) -> GeoCountry:
        """Retrieves a country by its two-letter code."""
        return self._http.request(
            ApiRequest("GET", f"/v2/geo/countries/{quote(country_code, safe='')}", options=options)
        )

    def search_countries(
        self,
        *,
        query: str | None = None,
        page_size: int | None = None,
        cursor: str | None = None,
        options: RequestOptions | None = None,
    ) -> GeoCountrySearchResponse:
        body = {"query": query, "pageSize": page_size, "cursor": cursor}
        return self._search("/v2/geo/countries", body, options)

    def search_countries_all(
        self,
        *,
        query: str | None = None,
        page_size: int | None = None,
        cursor: str | None = None,
        options: RequestOptions | None = None,
    ) -> Generator[GeoCountry, None]:
        return paginate(
            lambda next_cursor: self.search_countries(
                query=query, page_size=page_size, cursor=next_cursor, options=options
            ),
            cursor,
        )

    def search_states(
        self,
        *,
        country_codes: Sequence[str] | None = None,
        query: str | None = None,
        page_size: int | None = None,
        cursor: str | None = None,
        options: RequestOptions | None = None,
    ) -> GeoStateSearchResponse:
        body = {
            "countryCodes": country_codes,
            "query": query,
            "pageSize": page_size,
            "cursor": cursor,
        }
        return self._search("/v2/geo/states", body, options)

    def search_states_all(
        self,
        *,
        country_codes: Sequence[str] | None = None,
        query: str | None = None,
        page_size: int | None = None,
        cursor: str | None = None,
        options: RequestOptions | None = None,
    ) -> Generator[GeoState, None]:
        return paginate(
            lambda next_cursor: self.search_states(
                country_codes=country_codes,
                query=query,
                page_size=page_size,
                cursor=next_cursor,
                options=options,
            ),
            cursor,
        )

    def search_cities(
        self,
        *,
        state_ids: Sequence[int] | None = None,
        country_codes: Sequence[str] | None = None,
        query: str | None = None,
        page_size: int | None = None,
        cursor: str | None = None,
        options: RequestOptions | None = None,
    ) -> GeoCitySearchResponse:
        body = {
            "stateIds": state_ids,
            "countryCodes": country_codes,
            "query": query,
            "pageSize": page_size,
            "cursor": cursor,
        }
        return self._search("/v2/geo/cities", body, options)

    def search_cities_all(
        self,
        *,
        state_ids: Sequence[int] | None = None,
        country_codes: Sequence[str] | None = None,
        query: str | None = None,
        page_size: int | None = None,
        cursor: str | None = None,
        options: RequestOptions | None = None,
    ) -> Generator[GeoCity, None]:
        return paginate(
            lambda next_cursor: self.search_cities(
                state_ids=state_ids,
                country_codes=country_codes,
                query=query,
                page_size=page_size,
                cursor=next_cursor,
                options=options,
            ),
            cursor,
        )

    def _search(self, path: str, body: dict[str, Any], options: RequestOptions | None) -> Any:
        return self._http.request(
            ApiRequest("POST", path, body=compact(body), retry_safe=True, options=options)
        )
