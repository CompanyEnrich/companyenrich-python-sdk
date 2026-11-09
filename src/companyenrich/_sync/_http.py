# Generated from the _async package by scripts/unasync.py. Do not edit.

from __future__ import annotations

import time
from collections.abc import Generator, Callable, Mapping
from contextlib import closing
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


def sleep(seconds: float) -> None:
    time.sleep(seconds)


class HTTPClient:
    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        timeout: float | None,
        max_retries: int,
        default_headers: Mapping[str, str] | None,
        http_client: httpx.Client | None,
    ) -> None:
        self._api_key = resolve_api_key(api_key)
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._default_headers = default_headers
        self._client = http_client if http_client is not None else httpx.Client()
        self._owns_client = http_client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def request(self, request: ApiRequest) -> Any:
        """Sends a request and parses the JSON response."""
        response = self._execute(request, accept="application/json", stream=False)
        return parse_json(response.content, response.status_code)

    def stream_bytes(self, request: ApiRequest) -> Generator[bytes, None]:
        """Sends a request and yields the response body as it arrives."""
        response = self._execute(request, accept="*/*", stream=True)
        try:
            for chunk in response.iter_bytes():
                yield chunk
        except httpx.TimeoutException as error:
            raise APITimeoutError(f"Download timed out: {error}") from error
        except httpx.TransportError as error:
            raise APIConnectionError(f"Download was interrupted: {error}") from error
        finally:
            response.close()

    def stream_ndjson(self, request: ApiRequest) -> Generator[Any, None]:
        """Sends a request to an NDJSON endpoint and yields one parsed record per line."""
        decoder = NdjsonDecoder()
        with closing(self.stream_bytes(request)) as chunks:
            for chunk in chunks:
                for record in decoder.feed(chunk):
                    yield record
        for record in decoder.flush():
            yield record

    def _execute(self, request: ApiRequest, *, accept: str, stream: bool) -> httpx.Response:
        options = request.options or {}
        max_retries = options.get("max_retries", self._max_retries)
        retry_safe = request.can_retry_ambiguous_failure

        attempt = 0
        while True:
            failure: CompanyEnrichError
            delay: float | None
            try:
                response = self._client.send(self._build(request, accept), stream=True)
                if stream and response.is_success:
                    return response
                try:
                    response.read()
                finally:
                    response.close()
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
            sleep(delay)
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


def paginate(
    fetch_page: Callable[[str | None], Any], first_cursor: str | None = None
) -> Generator[Any, None]:
    """Lazily yields every item across pages, requesting a page only when it is needed."""
    cursor = first_cursor
    while True:
        page = fetch_page(cursor)
        for item in page["items"]:
            yield item
        cursor = page.get("nextCursor")
        if not cursor:
            return
