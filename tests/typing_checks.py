"""Checked by mypy only, never run.

mypy's strict mode rejects unused ignores, so each ignore below proves the SDK rejects that call.
"""

from __future__ import annotations

from typing_extensions import assert_type

from companyenrich import AsyncCompanyEnrich, CompanyEnrich
from companyenrich.types import (
    BatchStatus,
    Company,
    CompanyBulkEnrichmentResult,
    CompanySearchResponse,
    Person,
    PersonEmail,
    PersonSearchExportResult,
)

client = CompanyEnrich("key")

assert_type(client.companies.enrich("stripe.com"), Company)
assert_type(client.companies.search(page_size=1), CompanySearchResponse)
assert_type(client.people.get(1), Person)
assert_type(client.people.find_email(1), PersonEmail)
assert_type(client.batches.get("id"), BatchStatus)

for company in client.companies.search_all():
    assert_type(company, Company)

client.companies.search(
    filter={
        "country": "US",
        "employees": ["51-200"],
        "categories": "saas",
        "keywords": {"in": ["ai"], "notIn": ["crypto"]},
    }
)


def embedded_records_are_typed(
    bulk: CompanyBulkEnrichmentResult, export: PersonSearchExportResult
) -> None:
    company = bulk.get("company")
    if company is not None:
        assert_type(company["domain"], str)
    assert_type(export["person"]["id"], int)


async def async_results_are_typed(async_client: AsyncCompanyEnrich) -> None:
    assert_type(await async_client.companies.enrich("stripe.com"), Company)
    async for person in async_client.people.search_all():
        assert_type(person, Person)


client.companies.enrich()  # type: ignore[call-arg]
client.companies.enrich("a.com", expand=["nope"])  # type: ignore[list-item]
client.companies.search(filter={"employees": "nope"})  # type: ignore[arg-type]
client.companies.search(filter={"notAField": 1})  # type: ignore[arg-type]
client.people.search(page_size="ten")  # type: ignore[arg-type]
