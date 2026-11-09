from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import aclosing
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar
from urllib.parse import quote

from .._common import ApiRequest, RequestOptions
from ._http import AsyncHTTPClient

if TYPE_CHECKING:
    from ..types import BatchStatus

ResultsT = TypeVar("ResultsT")
RecordT = TypeVar("RecordT")


class AsyncBatchJob(Generic[ResultsT, RecordT]):
    """An asynchronous job: create it, wait with ``batches.wait_for_completion``, then download."""

    def __init__(self, http: AsyncHTTPClient, path: str) -> None:
        self._http = http
        self._path = path

    async def _create(self, body: dict[str, Any], options: RequestOptions | None) -> BatchStatus:
        return await self._http.request(ApiRequest("POST", self._path, body=body, options=options))

    async def results(
        self, batch_id: str, *, sig: str | None = None, options: RequestOptions | None = None
    ) -> ResultsT:
        """Downloads every settled record as one JSON document."""
        return await self._http.request(self._results_request(batch_id, "json", sig, options))

    def stream(
        self, batch_id: str, *, sig: str | None = None, options: RequestOptions | None = None
    ) -> AsyncGenerator[RecordT, None]:
        """Streams settled records one at a time. Prefer this for large jobs."""
        return self._http.stream_ndjson(self._results_request(batch_id, "ndjson", sig, options))

    async def csv(
        self, batch_id: str, *, sig: str | None = None, options: RequestOptions | None = None
    ) -> str:
        """Downloads the results as CSV text. Use ``iter_csv`` for large jobs."""
        chunks = []
        async with aclosing(self.iter_csv(batch_id, sig=sig, options=options)) as stream:
            async for chunk in stream:
                chunks.append(chunk)
        return b"".join(chunks).decode("utf-8-sig")

    def iter_csv(
        self, batch_id: str, *, sig: str | None = None, options: RequestOptions | None = None
    ) -> AsyncGenerator[bytes, None]:
        """Yields the CSV download as raw bytes, for example to write it to a file."""
        return self._http.stream_bytes(self._results_request(batch_id, "csv", sig, options))

    def _results_request(
        self,
        batch_id: str,
        format: Literal["json", "ndjson", "csv"],
        sig: str | None,
        options: RequestOptions | None,
    ) -> ApiRequest:
        return ApiRequest(
            "GET",
            f"{self._path}/{quote(batch_id, safe='')}/results",
            query={"format": format, "sig": sig},
            options=options,
        )
