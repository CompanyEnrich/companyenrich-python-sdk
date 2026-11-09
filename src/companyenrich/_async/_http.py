from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Callable, Mapping
from contextlib import aclosing
from typing import Any

import httpx

from .._common import (
    ApiRequest,
    NdjsonDecoder,
    backoff,
    build_headers,
    build_query,
    parse_error_body,
    parse_json,
    resolve_api_key,
    retry_delay,
)
from .._errors import APIConnectionError, APITimeoutError, CompanyEnrichError, create_api_error


async def sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


class AsyncHTTPClient:
    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        timeout: float | None,
        max_retries: int,
        default_headers: Mapping[str, str] | None,
        http_client: httpx.AsyncClient | None,
    ) -> None:
        self._api_key = resolve_api_key(api_key)
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._default_headers = default_headers
        self._client = http_client if http_client is not None else httpx.AsyncClient()
        self._owns_client = http_client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def request(self, request: ApiRequest) -> Any:
        """Sends a request and parses the JSON response."""
        response = await self._execute(request, accept="application/json", stream=False)
        return parse_json(response.content, response.status_code)

    async def stream_bytes(self, request: ApiRequest) -> AsyncGenerator[bytes, None]:
        """Sends a request and yields the response body as it arrives."""
        response = await self._execute(request, accept="*/*", stream=True)
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        except httpx.TimeoutException as error:
            raise APITimeoutError(f"Download timed out: {error}") from error
        except httpx.TransportError as error:
            raise APIConnectionError(f"Download was interrupted: {error}") from error
        finally:
            await response.aclose()

    async def stream_ndjson(self, request: ApiRequest) -> AsyncGenerator[Any, None]:
        """Sends a request to an NDJSON endpoint and yields one parsed record per line."""
        decoder = NdjsonDecoder()
        async with aclosing(self.stream_bytes(request)) as chunks:
            async for chunk in chunks:
                for record in decoder.feed(chunk):
                    yield record
        for record in decoder.flush():
            yield record

    async def _execute(self, request: ApiRequest, *, accept: str, stream: bool) -> httpx.Response:
        options = request.options or {}
        max_retries = options.get("max_retries", self._max_retries)
        retry_safe = request.can_retry_ambiguous_failure

        attempt = 0
        while True:
            failure: CompanyEnrichError
            delay: float | None
            try:
                response = await self._client.send(self._build(request, accept), stream=True)
                if stream and response.is_success:
                    return response
                try:
                    await response.aread()
                finally:
                    await response.aclose()
                if response.is_success:
                    return response
                status = response.status_code
                failure = create_api_error(status, response.headers, parse_error_body(response))
                delay = retry_delay(status, response.headers, attempt, retry_safe)
            except httpx.TimeoutException as error:
                failure = APITimeoutError(f"Request timed out: {error}")
                failure.__cause__ = error
                delay = backoff(attempt) if retry_safe else None
            except httpx.TransportError as error:
                failure = APIConnectionError(f"Could not reach the CompanyEnrich API: {error}")
                failure.__cause__ = error
                delay = backoff(attempt) if retry_safe else None

            if delay is None or attempt >= max_retries:
                raise failure
            await sleep(delay)
            attempt += 1

    def _build(self, request: ApiRequest, accept: str) -> httpx.Request:
        options = request.options or {}
        return self._client.build_request(
            request.method,
            f"{self._base_url}{request.path}",
            params=build_query(request.query),
            json=request.body,
            headers=build_headers(self._api_key, accept, self._default_headers, options),
            timeout=options.get("timeout", self._timeout),
        )


async def paginate(
    fetch_page: Callable[[str | None], Any], first_cursor: str | None = None
) -> AsyncGenerator[Any, None]:
    """Lazily yields every item across pages, requesting a page only when it is needed."""
    cursor = first_cursor
    while True:
        page = await fetch_page(cursor)
        for item in page["items"]:
            yield item
        cursor = page.get("nextCursor")
        if not cursor:
            return
