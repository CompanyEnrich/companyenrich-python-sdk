from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from companyenrich import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AsyncCompanyEnrich,
    AuthenticationError,
    BadRequestError,
    CompanyEnrichError,
    NotFoundError,
    PaymentRequiredError,
    PermissionDeniedError,
    RateLimitError,
    ServerError,
    ValidationError,
)
from tests._async.support import client_with
from tests.helpers import json_response, problem


async def test_sends_the_bearer_token_to_the_production_api() -> None:
    client, recorder = client_with([json_response({"userId": "u"})])
    await client.me()
    request = recorder.requests[0]
    assert str(request.url) == "https://api.companyenrich.com/v2/me"
    assert request.method == "GET"
    assert request.headers["authorization"] == "Bearer test-key"
    assert request.headers["user-agent"].startswith("companyenrich-python/")
    assert "content-type" not in request.headers


async def test_reads_the_api_key_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPANYENRICH_API_KEY", "env-key")
    transport = httpx.MockTransport(lambda request: json_response(dict(request.headers)))
    client = AsyncCompanyEnrich(http_client=httpx.AsyncClient(transport=transport))
    response: Any = await client.me()
    assert response["authorization"] == "Bearer env-key"


@pytest.mark.parametrize("value", [None, ""])
def test_requires_an_api_key(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    monkeypatch.delenv("COMPANYENRICH_API_KEY", raising=False)
    if value is not None:
        monkeypatch.setenv("COMPANYENRICH_API_KEY", value)
    with pytest.raises(CompanyEnrichError, match="Missing API key"):
        AsyncCompanyEnrich()


async def test_repeats_list_params_and_omits_unset_ones() -> None:
    client, recorder = client_with([json_response({})])
    await client.companies.enrich(
        "stripe.com", expand=["financial", "workforce"], wait_for_enrichment=False
    )
    params = recorder.requests[0].url.params
    assert params["domain"] == "stripe.com"
    assert params.get_list("expand") == ["financial", "workforce"]
    assert params["waitForEnrichment"] == "false"
    assert "cursor" not in params


async def test_sends_an_empty_object_for_an_unfiltered_search() -> None:
    client, recorder = client_with([json_response({"items": []})])
    await client.companies.search()
    request = recorder.requests[0]
    assert request.method == "POST"
    assert request.content == b"{}"
    assert request.headers["content-type"] == "application/json"


async def test_maps_snake_case_arguments_to_api_field_names() -> None:
    client, recorder = client_with([json_response({"items": []})])
    await client.companies.search(page_size=5, cursor="c", filter={"country": "US"})
    assert json.loads(recorder.requests[0].content) == {
        "pageSize": 5,
        "cursor": "c",
        "filter": {"country": "US"},
    }


async def test_encodes_path_params_and_keeps_large_person_ids_exact() -> None:
    large = 9007199254740993
    client, recorder = client_with([json_response({}), json_response({"id": large})])
    await client.geo.country("a/b")
    person = await client.people.get(large)
    assert recorder.requests[0].url.raw_path == b"/v2/geo/countries/a%2Fb"
    assert recorder.requests[1].url.path == f"/v2/people/{large}"
    assert person["id"] == large


async def test_merges_headers_and_trims_the_base_url() -> None:
    client, recorder = client_with(
        [json_response({})],
        base_url="https://proxy.example.com/ce/",
        default_headers={"x-team": "growth", "x-override": "default"},
    )
    await client.me(options={"headers": {"x-override": "request"}})
    request = recorder.requests[0]
    assert str(request.url) == "https://proxy.example.com/ce/v2/me"
    assert request.headers["x-team"] == "growth"
    assert request.headers["x-override"] == "request"


async def test_applies_timeouts_per_client_and_per_request() -> None:
    client, recorder = client_with([json_response({}), json_response({})], timeout=30.0)
    await client.me()
    await client.me(options={"timeout": None})
    assert recorder.requests[0].extensions["timeout"]["read"] == 30.0
    assert recorder.requests[1].extensions["timeout"]["read"] is None


@pytest.mark.parametrize(
    ("status", "error_class"),
    [
        (400, BadRequestError),
        (401, AuthenticationError),
        (402, PaymentRequiredError),
        (403, PermissionDeniedError),
        (404, NotFoundError),
        (422, ValidationError),
        (429, RateLimitError),
        (500, ServerError),
        (503, ServerError),
        (413, APIError),
    ],
)
async def test_maps_statuses_to_error_classes(status: int, error_class: type[APIError]) -> None:
    client, _ = client_with([problem(status)], max_retries=0)
    with pytest.raises(APIError) as caught:
        await client.me()
    assert type(caught.value) is error_class
    assert isinstance(caught.value, CompanyEnrichError)
    assert caught.value.status == status


async def test_exposes_problem_details_and_the_trace_id() -> None:
    body = {"title": "Unauthorized", "detail": "Invalid token.", "type": "about:blank"}
    client, _ = client_with([problem(401, body, {"x-trace-id": "trace-123"})])
    with pytest.raises(AuthenticationError) as caught:
        await client.me()
    assert str(caught.value) == "401 Unauthorized: Invalid token."
    assert caught.value.title == "Unauthorized"
    assert caught.value.detail == "Invalid token."
    assert caught.value.type == "about:blank"
    assert caught.value.trace_id == "trace-123"


async def test_includes_field_level_validation_messages() -> None:
    errors = {"domain": ["Required", "Too short"]}
    client, _ = client_with([problem(422, {"title": "Validation", "errors": errors})])
    with pytest.raises(ValidationError) as caught:
        await client.me()
    assert caught.value.errors == errors
    assert "domain: Required, Too short" in str(caught.value)


async def test_keeps_non_json_error_bodies() -> None:
    client, _ = client_with([httpx.Response(502, text="<html>Bad</html>")], max_retries=0)
    with pytest.raises(ServerError) as caught:
        await client.me()
    assert caught.value.body == "<html>Bad</html>"
    assert str(caught.value) == "502"


async def test_reports_a_malformed_success_body_without_retrying() -> None:
    client, recorder = client_with([httpx.Response(200, text="not json")])
    with pytest.raises(CompanyEnrichError, match="invalid JSON"):
        await client.me()
    assert len(recorder.requests) == 1


async def test_retries_a_429_on_a_paid_post_honoring_retry_after(delays: list[float]) -> None:
    client, recorder = client_with(
        [problem(429, headers={"retry-after": "3"}), json_response({"items": []})]
    )
    assert await client.companies.search(page_size=1) == {"items": []}
    assert len(recorder.requests) == 2
    assert delays == [3.0]


async def test_waits_for_the_rate_limit_window_on_a_429(delays: list[float]) -> None:
    client, recorder = client_with(
        [problem(429, headers={"x-ratelimit-window": "00:00:35.5000000"}), json_response({})]
    )
    await client.me()
    assert len(recorder.requests) == 2
    assert delays == [35.5]


async def test_stops_when_the_server_asks_for_an_unreasonable_wait() -> None:
    client, recorder = client_with([problem(429, headers={"retry-after": "3600"})])
    with pytest.raises(RateLimitError):
        await client.me()
    assert len(recorder.requests) == 1


@pytest.mark.parametrize("status", [500, 502, 503, 504])
async def test_retries_a_get_on_server_errors(status: int, delays: list[float]) -> None:
    client, recorder = client_with([problem(status), json_response({"userId": "u"})])
    assert (await client.me())["userId"] == "u"
    assert len(recorder.requests) == 2
    assert 0.375 <= delays[0] <= 0.5


@pytest.mark.parametrize(
    "failure", [httpx.ConnectError("refused"), httpx.ReadTimeout("slow"), httpx.ReadError("reset")]
)
async def test_retries_a_get_after_a_transport_failure(failure: Exception) -> None:
    client, recorder = client_with([failure, json_response({"userId": "u"})])
    assert (await client.me())["userId"] == "u"
    assert len(recorder.requests) == 2


Paid = Callable[[AsyncCompanyEnrich], Any]
PAID_POSTS: list[tuple[str, Paid]] = [
    ("company search", lambda c: c.companies.search()),
    ("people search", lambda c: c.people.search()),
    ("enrich by properties", lambda c: c.companies.enrich_by_properties(name="x")),
    ("batch enrich", lambda c: c.companies.enrich_batch(["a.com"])),
    ("bulk enrichment", lambda c: c.companies.bulk_enrichment.create(["a.com"])),
    ("company export", lambda c: c.companies.search_export.create(1)),
    ("people export", lambda c: c.people.search_export.create(1)),
    ("person enrich", lambda c: c.people.enrich("a@b.co")),
]


@pytest.mark.parametrize(("name", "call"), PAID_POSTS, ids=[name for name, _ in PAID_POSTS])
async def test_never_repeats_a_paid_post_after_an_ambiguous_failure(name: str, call: Paid) -> None:
    server_client, server = client_with([problem(503)])
    with pytest.raises(ServerError):
        await call(server_client)
    assert len(server.requests) == 1

    network_client, network = client_with([httpx.ReadError("reset")])
    with pytest.raises(APIConnectionError):
        await call(network_client)
    assert len(network.requests) == 1

    timeout_client, timed_out = client_with([httpx.ReadTimeout("slow")])
    with pytest.raises(APITimeoutError):
        await call(timeout_client)
    assert len(timed_out.requests) == 1


FREE_POSTS: list[tuple[str, Paid]] = [
    ("company count", lambda c: c.companies.count()),
    ("company preview", lambda c: c.companies.preview()),
    ("people count", lambda c: c.people.count()),
    ("people preview", lambda c: c.people.preview()),
    ("country search", lambda c: c.geo.search_countries()),
    ("state search", lambda c: c.geo.search_states()),
    ("city search", lambda c: c.geo.search_cities()),
    ("batch cancel", lambda c: c.batches.cancel("id")),
]


@pytest.mark.parametrize(("name", "call"), FREE_POSTS, ids=[name for name, _ in FREE_POSTS])
async def test_retries_free_post_endpoints(name: str, call: Paid) -> None:
    client, recorder = client_with([problem(500), json_response({})])
    await call(client)
    assert len(recorder.requests) == 2


async def test_does_not_retry_client_errors() -> None:
    client, recorder = client_with([problem(404)])
    with pytest.raises(NotFoundError):
        await client.me()
    assert len(recorder.requests) == 1


async def test_gives_up_after_max_retries() -> None:
    client, recorder = client_with([problem(503), problem(503), problem(503)], max_retries=2)
    with pytest.raises(ServerError):
        await client.me()
    assert len(recorder.requests) == 3


async def test_a_request_can_override_max_retries() -> None:
    client, recorder = client_with([problem(503)])
    with pytest.raises(ServerError):
        await client.me(options={"max_retries": 0})
    assert len(recorder.requests) == 1


async def test_chains_the_original_transport_error() -> None:
    original = httpx.ConnectError("refused")
    client, _ = client_with([original], max_retries=0)
    with pytest.raises(APIConnectionError) as caught:
        await client.me()
    assert caught.value.__cause__ is original


async def test_closes_a_client_it_created_but_not_one_it_was_given() -> None:
    transport = httpx.MockTransport(lambda request: json_response({}))
    injected = httpx.AsyncClient(transport=transport)
    async with AsyncCompanyEnrich("k", http_client=injected) as client:
        await client.me()
    assert not injected.is_closed

    async with AsyncCompanyEnrich("k") as owned:
        internal = owned._http._client
    assert internal.is_closed
