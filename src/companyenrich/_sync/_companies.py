# Generated from the _async package by scripts/unasync.py. Do not edit.

from __future__ import annotations

from collections.abc import Generator, Sequence
from typing import TYPE_CHECKING
from urllib.parse import quote

from .._common import ApiRequest, RequestOptions, compact
from ._batch_job import BatchJob
from ._http import HTTPClient, paginate

if TYPE_CHECKING:
    from ..types import (
        BatchStatus,
        Company,
        CompanyAutocompleteResponse,
        CompanyBulkEnrichmentResult,  # noqa: F401
        CompanyBulkEnrichmentResults,  # noqa: F401
        CompanyExpansion,
        CompanyLookalikeQuery,
        CompanySearchCount,
        CompanySearchExportResult,  # noqa: F401
        CompanySearchExportResults,  # noqa: F401
        CompanySearchFilter,
        CompanySearchPreview,
        CompanySearchResponse,
        CompanySemanticQuery,
        CompanyWorkforce,
        EnrichCompaniesBatchResponse,
    )


class CompanyBulkEnrichment(
    BatchJob["CompanyBulkEnrichmentResults", "CompanyBulkEnrichmentResult"]
):
    """Asynchronous enrichment of up to 10,000 domains."""

    def create(
        self,
        domains: Sequence[str],
        *,
        expand: Sequence[CompanyExpansion] | None = None,
        wait_for_enrichment: bool | None = None,
        options: RequestOptions | None = None,
    ) -> BatchStatus:
        """Starts the job. It runs in the background and consumes credits as it progresses."""
        body = compact(
            {"domains": domains, "expand": expand, "waitForEnrichment": wait_for_enrichment}
        )
        return self._create(body, options)


class CompanySearchExport(
    BatchJob["CompanySearchExportResults", "CompanySearchExportResult"]
):
    """Asynchronous export of a company search."""

    def create(
        self,
        limit: int,
        *,
        filter: CompanySearchFilter | None = None,
        semantic: CompanySemanticQuery | None = None,
        lookalike: CompanyLookalikeQuery | None = None,
        expand: Sequence[CompanyExpansion] | None = None,
        options: RequestOptions | None = None,
    ) -> BatchStatus:
        """Starts the export. It runs in the background and consumes credits as it progresses."""
        body = compact(
            {
                "limit": limit,
                "filter": filter,
                "semantic": semantic,
                "lookalike": lookalike,
                "expand": expand,
            }
        )
        return self._create(body, options)


class Companies:
    def __init__(self, http: HTTPClient) -> None:
        self._http = http
        self.bulk_enrichment = CompanyBulkEnrichment(http, "/v2/companies/enrich/bulk")
        self.search_export = CompanySearchExport(http, "/v2/companies/search/export")

    def get(
        self,
        company_id: str,
        *,
        expand: Sequence[CompanyExpansion] | None = None,
        options: RequestOptions | None = None,
    ) -> Company:
        """Retrieves a stored company by its CompanyEnrich ID."""
        return self._http.request(
            ApiRequest(
                "GET",
                f"/v2/companies/{quote(company_id, safe='')}",
                query={"expand": expand},
                options=options,
            )
        )

    def enrich(
        self,
        domain: str,
        *,
        expand: Sequence[CompanyExpansion] | None = None,
        wait_for_enrichment: bool | None = None,
        options: RequestOptions | None = None,
    ) -> Company:
        """Enriches a company by domain. Raises ``NotFoundError`` when there is no match."""
        query = {"domain": domain, "expand": expand, "waitForEnrichment": wait_for_enrichment}
        return self._http.request(
            ApiRequest("GET", "/v2/companies/enrich", query=query, options=options)
        )

    def enrich_by_properties(
        self,
        *,
        name: str | None = None,
        linkedin_url: str | None = None,
        linkedin_id: str | None = None,
        twitter_url: str | None = None,
        facebook_url: str | None = None,
        instagram_url: str | None = None,
        youtube_url: str | None = None,
        expand: Sequence[CompanyExpansion] | None = None,
        options: RequestOptions | None = None,
    ) -> Company:
        """Enriches a company from identifying properties such as its name or LinkedIn URL."""
        body = compact(
            {
                "name": name,
                "linkedinUrl": linkedin_url,
                "linkedinId": linkedin_id,
                "twitterUrl": twitter_url,
                "facebookUrl": facebook_url,
                "instagramUrl": instagram_url,
                "youtubeUrl": youtube_url,
                "expand": expand,
            }
        )
        return self._http.request(
            ApiRequest("POST", "/v2/companies/enrich", body=body, options=options)
        )

    def enrich_batch(
        self,
        domains: Sequence[str],
        *,
        expand: Sequence[CompanyExpansion] | None = None,
        wait_for_enrichment: bool | None = None,
        options: RequestOptions | None = None,
    ) -> EnrichCompaniesBatchResponse:
        """Enriches up to 50 domains in one request."""
        body = compact(
            {"domains": domains, "expand": expand, "waitForEnrichment": wait_for_enrichment}
        )
        return self._http.request(
            ApiRequest("POST", "/v2/companies/enrich/batch", body=body, options=options)
        )

    def autocomplete(
        self, query: str, *, options: RequestOptions | None = None
    ) -> CompanyAutocompleteResponse:
        """Suggests up to 10 companies whose domain matches ``query``."""
        return self._http.request(
            ApiRequest("GET", "/v2/companies/autocomplete", query={"query": query}, options=options)
        )

    def workforce(
        self,
        *,
        company_id: str | None = None,
        domain: str | None = None,
        cursor: str | None = None,
        options: RequestOptions | None = None,
    ) -> CompanyWorkforce:
        """Retrieves workforce insights for exactly one of ``company_id`` or ``domain``.

        Pass ``nextCursor`` from the response as ``cursor`` to go back another 12 months.
        """
        if (company_id is None) == (domain is None):
            raise ValueError("Provide exactly one of `company_id` or `domain`.")
        query = {"id": company_id, "domain": domain, "cursor": cursor}
        return self._http.request(
            ApiRequest("GET", "/v2/companies/workforce", query=query, options=options)
        )

    def search(
        self,
        *,
        filter: CompanySearchFilter | None = None,
        semantic: CompanySemanticQuery | None = None,
        lookalike: CompanyLookalikeQuery | None = None,
        page_size: int | None = None,
        cursor: str | None = None,
        expand: Sequence[CompanyExpansion] | None = None,
        options: RequestOptions | None = None,
    ) -> CompanySearchResponse:
        """Returns one page of companies matching filters, a semantic query, or lookalike seeds."""
        body = compact(
            {
                "filter": filter,
                "semantic": semantic,
                "lookalike": lookalike,
                "pageSize": page_size,
                "cursor": cursor,
                "expand": expand,
            }
        )
        return self._http.request(
            ApiRequest("POST", "/v2/companies/search", body=body, options=options)
        )

    def search_all(
        self,
        *,
        filter: CompanySearchFilter | None = None,
        semantic: CompanySemanticQuery | None = None,
        lookalike: CompanyLookalikeQuery | None = None,
        page_size: int | None = None,
        cursor: str | None = None,
        expand: Sequence[CompanyExpansion] | None = None,
        options: RequestOptions | None = None,
    ) -> Generator[Company, None]:
        """Iterates over every matching company, fetching pages as needed.

        Credits are charged per page, so set ``page_size`` close to what you will consume.
        """
        return paginate(
            lambda next_cursor: self.search(
                filter=filter,
                semantic=semantic,
                lookalike=lookalike,
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
        filter: CompanySearchFilter | None = None,
        semantic: CompanySemanticQuery | None = None,
        lookalike: CompanyLookalikeQuery | None = None,
        options: RequestOptions | None = None,
    ) -> CompanySearchCount:
        """Counts matching companies. Free."""
        body = compact({"filter": filter, "semantic": semantic, "lookalike": lookalike})
        return self._http.request(
            ApiRequest(
                "POST", "/v2/companies/search/count", body=body, retry_safe=True, options=options
            )
        )

    def preview(
        self,
        *,
        filter: CompanySearchFilter | None = None,
        semantic: CompanySemanticQuery | None = None,
        lookalike: CompanyLookalikeQuery | None = None,
        options: RequestOptions | None = None,
    ) -> CompanySearchPreview:
        """Returns up to 25 company summaries. Free, but requires a plan with previews."""
        body = compact({"filter": filter, "semantic": semantic, "lookalike": lookalike})
        return self._http.request(
            ApiRequest(
                "POST", "/v2/companies/search/preview", body=body, retry_safe=True, options=options
            )
        )
