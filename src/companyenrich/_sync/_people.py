# Generated from the _async package by scripts/unasync.py. Do not edit.

from __future__ import annotations

from collections.abc import Generator, Sequence
from typing import TYPE_CHECKING

from .._common import ApiRequest, RequestOptions, compact
from ._batch_job import BatchJob
from ._http import HTTPClient, paginate

if TYPE_CHECKING:
    from ..types import (
        BatchStatus,
        CompanyQuery,
        Person,
        PersonEmail,
        PersonExpansion,
        PersonSearchCount,
        PersonSearchExportResult,  # noqa: F401
        PersonSearchExportResults,  # noqa: F401
        PersonSearchFilter,
        PersonSearchPreview,
        PersonSearchResponse,
        PersonSemanticQuery,
    )


class PersonSearchExport(
    BatchJob["PersonSearchExportResults", "PersonSearchExportResult"]
):
    """Asynchronous export of a people search."""

    def create(
        self,
        limit: int,
        *,
        filter: PersonSearchFilter | None = None,
        semantic: PersonSemanticQuery | None = None,
        company: CompanyQuery | None = None,
        expand: Sequence[PersonExpansion] | None = None,
        options: RequestOptions | None = None,
    ) -> BatchStatus:
        """Starts the export. It runs in the background and consumes credits as it progresses."""
        body = compact(
            {
                "limit": limit,
                "filter": filter,
                "semantic": semantic,
                "company": company,
                "expand": expand,
            }
        )
        return self._create(body, options)


class People:
    def __init__(self, http: HTTPClient) -> None:
        self._http = http
        self.search_export = PersonSearchExport(http, "/v2/people/search/export")

    def get(
        self,
        person_id: int,
        *,
        expand: Sequence[PersonExpansion] | None = None,
        options: RequestOptions | None = None,
    ) -> Person:
        """Retrieves a person by their CompanyEnrich ID."""
        return self._http.request(
            ApiRequest(
                "GET", f"/v2/people/{int(person_id)}", query={"expand": expand}, options=options
            )
        )

    def enrich(
        self,
        email: str,
        *,
        expand: Sequence[PersonExpansion] | None = None,
        options: RequestOptions | None = None,
    ) -> Person:
        """Identifies a person from an email. Raises ``NotFoundError`` if there is no match."""
        body = compact({"email": email, "expand": expand})
        return self._http.request(
            ApiRequest("POST", "/v2/people/enrich", body=body, options=options)
        )

    def find_email(
        self,
        person_id: int,
        *,
        domain: str | None = None,
        options: RequestOptions | None = None,
    ) -> PersonEmail:
        """Finds a person's work email. Check ``status``: only ``found`` includes ``email``."""
        return self._http.request(
            ApiRequest(
                "GET",
                f"/v2/people/{int(person_id)}/email",
                query={"domain": domain},
                options=options,
            )
        )

    def search(
        self,
        *,
        filter: PersonSearchFilter | None = None,
        semantic: PersonSemanticQuery | None = None,
        company: CompanyQuery | None = None,
        page_size: int | None = None,
        cursor: str | None = None,
        expand: Sequence[PersonExpansion] | None = None,
        options: RequestOptions | None = None,
    ) -> PersonSearchResponse:
        """Returns one page of people matching filters, a semantic query, or a company query."""
        body = compact(
            {
                "filter": filter,
                "semantic": semantic,
                "company": company,
                "pageSize": page_size,
                "cursor": cursor,
                "expand": expand,
            }
        )
        return self._http.request(
            ApiRequest("POST", "/v2/people/search", body=body, options=options)
        )

    def search_all(
        self,
        *,
        filter: PersonSearchFilter | None = None,
        semantic: PersonSemanticQuery | None = None,
        company: CompanyQuery | None = None,
        page_size: int | None = None,
        cursor: str | None = None,
        expand: Sequence[PersonExpansion] | None = None,
        options: RequestOptions | None = None,
    ) -> Generator[Person, None]:
        """Iterates over every matching person, fetching pages as needed.

        Credits are charged per page, so set ``page_size`` close to what you will consume.
        """
        return paginate(
            lambda next_cursor: self.search(
                filter=filter,
                semantic=semantic,
                company=company,
                page_size=page_size,
                cursor=next_cursor,
                expand=expand,
                options=options,
            ),
            cursor,
        )

    def count(
        self,
        *,
        filter: PersonSearchFilter | None = None,
        semantic: PersonSemanticQuery | None = None,
        company: CompanyQuery | None = None,
        options: RequestOptions | None = None,
    ) -> PersonSearchCount:
        """Counts matching people. Free."""
        body = compact({"filter": filter, "semantic": semantic, "company": company})
        return self._http.request(
            ApiRequest(
                "POST", "/v2/people/search/count", body=body, retry_safe=True, options=options
            )
        )

    def preview(
        self,
        *,
        filter: PersonSearchFilter | None = None,
        semantic: PersonSemanticQuery | None = None,
        company: CompanyQuery | None = None,
        options: RequestOptions | None = None,
    ) -> PersonSearchPreview:
        """Returns up to 10 person summaries. Free, but requires a plan with previews."""
        body = compact({"filter": filter, "semantic": semantic, "company": company})
        return self._http.request(
            ApiRequest(
                "POST", "/v2/people/search/preview", body=body, retry_safe=True, options=options
            )
        )
