from __future__ import annotations

import inspect
import json
import re
from collections.abc import Callable
from contextlib import aclosing
from pathlib import Path
from typing import Any

import httpx
import pytest

from companyenrich import (
    APIConnectionError,
    APITimeoutError,
    AsyncCompanyEnrich,
    NotFoundError,
)
from tests._async.support import client_with
from tests.helpers import ChunkStream, json_response, problem

UUID = "00000000-0000-4000-8000-000000000001"
Invoke = Callable[[AsyncCompanyEnrich], Any]

# Every operation in the OpenAPI spec and the SDK call that reaches it.
OPERATIONS: dict[str, Invoke] = {
    "GET /v2/companies/{companyId}": lambda c: c.companies.get(UUID, expand=["keywords"]),
    "GET /v2/companies/enrich": lambda c: c.companies.enrich("stripe.com"),
    "POST /v2/companies/enrich": lambda c: c.companies.enrich_by_properties(name="Stripe"),
    "POST /v2/companies/enrich/batch": lambda c: c.companies.enrich_batch(["stripe.com"]),
    "GET /v2/companies/autocomplete": lambda c: c.companies.autocomplete("stri"),
    "POST /v2/companies/enrich/bulk": lambda c: c.companies.bulk_enrichment.create(["a.com"]),
    "POST /v2/companies/search/export": lambda c: c.companies.search_export.create(10),
    "POST /v2/people/search/export": lambda c: c.people.search_export.create(10),
    "GET /v2/companies/enrich/bulk/{id}/results": lambda c: c.companies.bulk_enrichment.results(
        UUID
    ),
    "GET /v2/companies/search/export/{id}/results": lambda c: c.companies.search_export.results(
        UUID
    ),
    "GET /v2/people/search/export/{id}/results": lambda c: c.people.search_export.results(UUID),
    "GET /v2/companies/workforce": lambda c: c.companies.workforce(domain="stripe.com"),
    "POST /v2/companies/search": lambda c: c.companies.search(page_size=1),
    "POST /v2/companies/search/count": lambda c: c.companies.count(),
    "POST /v2/companies/search/preview": lambda c: c.companies.preview(),
    "POST /v2/people/search": lambda c: c.people.search(page_size=1),
    "POST /v2/people/search/count": lambda c: c.people.count(),
    "POST /v2/people/search/preview": lambda c: c.people.preview(),
    "GET /v2/industries": lambda c: c.industries.list(),
    "GET /v2/keywords/autocomplete": lambda c: c.keywords.autocomplete("saas"),
    "GET /v2/technologies/autocomplete": lambda c: c.technologies.autocomplete("react"),
    "GET /v2/positions/autocomplete": lambda c: c.positions.autocomplete("cto"),
    "GET /v2/me": lambda c: c.me(),
    "GET /v2/batches": lambda c: c.batches.list(page_size=5),
    "GET /v2/batches/{id}": lambda c: c.batches.get(UUID),
    "POST /v2/batches/{id}/cancel": lambda c: c.batches.cancel(UUID),
    "GET /v2/batches/{id}/results": lambda c: c.batches.raw_results(UUID),
    "GET /v2/people/{personId}": lambda c: c.people.get(42),
    "POST /v2/people/enrich": lambda c: c.people.enrich("a@b.co"),
    "GET /v2/people/{personId}/email": lambda c: c.people.find_email(42),
    "GET /v2/geo/regions": lambda c: c.geo.regions(),
    "GET /v2/geo/countries/{countryCode}": lambda c: c.geo.country("US"),
    "POST /v2/geo/countries": lambda c: c.geo.search_countries(query="uni"),
    "POST /v2/geo/states": lambda c: c.geo.search_states(query="cal"),
    "POST /v2/geo/cities": lambda c: c.geo.search_cities(query="par"),
}


def spec_operations() -> list[str]:
    spec = json.loads((Path(__file__).parents[2] / "openapi" / "v2.json").read_text("utf-8"))
    return [
        f"{method.upper()} {path}"
        for path, item in spec["paths"].items()
        for method in item
        if method in {"get", "post", "put", "patch", "delete"}
    ]


def test_every_spec_operation_is_mapped() -> None:
    assert sorted(OPERATIONS) == sorted(spec_operations())


@pytest.mark.parametrize("operation", sorted(OPERATIONS))
async def test_operation_reaches_its_endpoint(operation: str) -> None:
    method, template = operation.split(" ")
    client, recorder = client_with([json_response({"items": []})])
    result = OPERATIONS[operation](client)
    if inspect.isawaitable(result):
        await result
    else:
        async for _ in result:
            pass
    request = recorder.requests[0]
    assert request.method == method
    assert re.fullmatch(re.sub(r"\{[^}]+\}", "[^/]+", template), request.url.path)


async def collect(iterator: Any) -> list[Any]:
    return [item async for item in iterator]


async def test_walks_every_page_forwarding_the_cursor_and_params() -> None:
    client, recorder = client_with(
        [
            json_response({"items": [{"id": "1"}, {"id": "2"}], "nextCursor": "c2"}),
            json_response({"items": [{"id": "3"}], "nextCursor": "c3"}),
            json_response({"items": [{"id": "4"}]}),
        ]
    )
    companies = await collect(client.companies.search_all(page_size=2))
    assert [company["id"] for company in companies] == ["1", "2", "3", "4"]
    bodies = [json.loads(request.content) for request in recorder.requests]
    assert bodies == [
        {"pageSize": 2},
        {"pageSize": 2, "cursor": "c2"},
        {"pageSize": 2, "cursor": "c3"},
    ]


async def test_does_not_fetch_another_page_after_the_caller_stops() -> None:
    client, recorder = client_with(
        [json_response({"items": [{"id": 1}, {"id": 2}], "nextCursor": "c2"})]
    )
    async for person in client.people.search_all(page_size=2):
        assert person["id"] == 1
        break
    assert len(recorder.requests) == 1


async def test_starts_from_a_caller_supplied_cursor() -> None:
    client, recorder = client_with([json_response({"items": []})])
    await collect(client.geo.search_cities_all(cursor="resume"))
    assert json.loads(recorder.requests[0].content) == {"cursor": "resume"}


async def test_paginates_batches_through_the_query_string() -> None:
    client, recorder = client_with(
        [
            json_response({"items": [{"id": "a"}], "nextCursor": "next"}),
            json_response({"items": [{"id": "b"}]}),
        ]
    )
    batches = await collect(client.batches.list_all(kind="company-enrichment"))
    assert [batch["id"] for batch in batches] == ["a", "b"]
    params = recorder.requests[1].url.params
    assert params["cursor"] == "next"
    assert params["kind"] == "company-enrichment"


async def test_surfaces_a_failure_on_a_later_page() -> None:
    client, _ = client_with(
        [json_response({"items": [{"id": "1"}], "nextCursor": "c2"}), problem(404)]
    )
    with pytest.raises(NotFoundError):
        await collect(client.companies.search_all())


async def test_selects_the_download_format_and_forwards_the_signature() -> None:
    client, recorder = client_with([json_response({"results": []})])
    await client.companies.search_export.results(UUID, sig="abc")
    url = recorder.requests[0].url
    assert url.path == f"/v2/companies/search/export/{UUID}/results"
    assert url.params["format"] == "json"
    assert url.params["sig"] == "abc"


async def test_streams_ndjson_across_chunk_boundaries() -> None:
    encoded = '{"index":0,"domain":"café.com"}\n{"index":1'.encode()
    split = encoded.index(0xC3) + 1
    chunks = [
        encoded[:split],
        encoded[split:],
        b',"domain":"b.com"}\r\n\n{"index":2,"domain":"c.com"}',
    ]
    client, recorder = client_with([httpx.Response(200, stream=ChunkStream(chunks))])
    records = await collect(client.companies.bulk_enrichment.stream(UUID))
    assert [record["domain"] for record in records] == ["café.com", "b.com", "c.com"]
    assert recorder.requests[0].url.params["format"] == "ndjson"
    assert recorder.requests[0].headers["accept"] == "*/*"


async def test_closes_the_download_when_the_caller_stops_early() -> None:
    body = ChunkStream([b'{"index":0}\n', b'{"index":1}\n'])
    client, _ = client_with([httpx.Response(200, stream=body)])
    async with aclosing(client.people.search_export.stream(UUID)) as records:
        async for record in records:
            assert record["index"] == 0
            break
    assert body.closed


async def test_raises_sdk_errors_when_a_download_is_interrupted() -> None:
    interrupted = ChunkStream([b'{"index":0}\n'], httpx.ReadError("reset"))
    client, _ = client_with([httpx.Response(200, stream=interrupted)])
    with pytest.raises(APIConnectionError):
        await collect(client.batches.raw_results(UUID))

    slow = ChunkStream([], httpx.ReadTimeout("slow"))
    client, _ = client_with([httpx.Response(200, stream=slow)])
    with pytest.raises(APITimeoutError):
        await collect(client.batches.raw_results(UUID))


async def test_raises_the_api_error_instead_of_streaming_a_failed_response() -> None:
    client, _ = client_with([problem(404, {"title": "Not Found"})])
    with pytest.raises(NotFoundError):
        await collect(client.batches.raw_results(UUID))


async def test_returns_csv_text_and_strips_a_byte_order_mark() -> None:
    client, recorder = client_with(
        [httpx.Response(200, content=b"\xef\xbb\xbfindex,domain\n0,a.com\n")]
    )
    assert await client.companies.bulk_enrichment.csv(UUID) == "index,domain\n0,a.com\n"
    assert recorder.requests[0].url.params["format"] == "csv"


async def test_yields_raw_csv_bytes() -> None:
    body = ChunkStream([b"index,", b"domain\n"])
    client, _ = client_with([httpx.Response(200, stream=body)])
    assert await collect(client.people.search_export.iter_csv(UUID)) == [b"index,", b"domain\n"]


def status(value: str) -> httpx.Response:
    return json_response({"id": UUID, "status": value})


async def test_polls_until_the_batch_is_finished(delays: list[float]) -> None:
    client, recorder = client_with([status("pending"), status("running"), status("completed")])
    seen: list[str] = []
    batch = await client.batches.wait_for_completion(
        UUID, poll_interval=7.0, on_progress=lambda update: seen.append(update["status"])
    )
    assert batch["status"] == "completed"
    assert seen == ["pending", "running", "completed"]
    assert len(recorder.requests) == 3
    assert delays == [7.0, 7.0]


async def test_treats_cancelling_as_unfinished_and_cancelled_as_finished() -> None:
    client, _ = client_with([status("cancelling"), status("cancelled")])
    batch = await client.batches.wait_for_completion(UUID)
    assert batch["status"] == "cancelled"


async def test_raises_when_the_batch_deadline_passes() -> None:
    client, _ = client_with([status("running")])
    with pytest.raises(APITimeoutError, match="did not finish"):
        await client.batches.wait_for_completion(UUID, timeout=0)


@pytest.mark.parametrize("arguments", [{}, {"company_id": UUID, "domain": "a.com"}])
async def test_workforce_requires_exactly_one_lookup(arguments: dict[str, Any]) -> None:
    client, recorder = client_with([])
    with pytest.raises(ValueError, match="exactly one"):
        await client.companies.workforce(**arguments)
    assert recorder.requests == []


async def test_workforce_sends_the_company_id_as_id() -> None:
    client, recorder = client_with([json_response({})])
    await client.companies.workforce(company_id=UUID, cursor="older")
    params = recorder.requests[0].url.params
    assert params["id"] == UUID
    assert params["cursor"] == "older"
