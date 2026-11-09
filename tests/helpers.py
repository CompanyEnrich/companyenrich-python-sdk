from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any

import httpx


def json_response(body: Any, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=body)


def problem(
    status: int,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    return httpx.Response(
        status,
        json={"status": status, **(body or {})},
        headers={"content-type": "application/problem+json", **(headers or {})},
    )


class Recorder:
    """Plays back responses in order and records every request."""

    def __init__(self, responses: Sequence[httpx.Response | Exception]) -> None:
        self.queue = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if not self.queue:
            raise AssertionError("Unexpected extra request")
        item = self.queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class ChunkStream(httpx.SyncByteStream, httpx.AsyncByteStream):
    """A response body delivered in exact chunks, optionally failing at the end."""

    def __init__(self, chunks: Sequence[bytes], error: Exception | None = None) -> None:
        self.chunks = chunks
        self.error = error
        self.closed = False

    def __iter__(self) -> Iterator[bytes]:
        yield from self.chunks
        if self.error:
            raise self.error

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self.chunks:
            yield chunk
        if self.error:
            raise self.error

    def close(self) -> None:
        self.closed = True

    async def aclose(self) -> None:
        self.closed = True
