# Generated from the _async package by scripts/unasync.py. Do not edit.

from __future__ import annotations

import time
from collections.abc import Generator, Callable
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from .._common import DEFAULT_POLL_INTERVAL, ApiRequest, RequestOptions
from .._errors import APITimeoutError
from . import _http
from ._http import HTTPClient, paginate

if TYPE_CHECKING:
    from ..types import BatchList, BatchRawResult, BatchStatus


class Batches:
    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    def list(
        self,
        *,
        kind: str | None = None,
        page_size: int | None = None,
        cursor: str | None = None,
        options: RequestOptions | None = None,
    ) -> BatchList:
        """Returns one page of your batches, newest first."""
        query = {"kind": kind, "pageSize": page_size, "cursor": cursor}
        return self._http.request(
            ApiRequest("GET", "/v2/batches", query=query, options=options)
        )

    def list_all(
        self,
        *,
        kind: str | None = None,
        page_size: int | None = None,
        cursor: str | None = None,
        options: RequestOptions | None = None,
    ) -> Generator[BatchStatus, None]:
        """Iterates over all of your batches, newest first."""
        return paginate(
            lambda next_cursor: self.list(
                kind=kind, page_size=page_size, cursor=next_cursor, options=options
            ),
            cursor,
        )

    def get(self, batch_id: str, *, options: RequestOptions | None = None) -> BatchStatus:
        """Retrieves a batch's status and progress."""
        return self._http.request(
            ApiRequest("GET", f"/v2/batches/{quote(batch_id, safe='')}", options=options)
        )

    def cancel(self, batch_id: str, *, options: RequestOptions | None = None) -> BatchStatus:
        """Stops remaining work. Results that were already charged stay downloadable."""
        return self._http.request(
            ApiRequest(
                "POST",
                f"/v2/batches/{quote(batch_id, safe='')}/cancel",
                retry_safe=True,
                options=options,
            )
        )

    def raw_results(
        self, batch_id: str, *, sig: str | None = None, options: RequestOptions | None = None
    ) -> Generator[BatchRawResult, None]:
        """Streams the raw HTTP outcome of each request in the batch."""
        return self._http.stream_ndjson(
            ApiRequest(
                "GET",
                f"/v2/batches/{quote(batch_id, safe='')}/results",
                query={"sig": sig},
                options=options,
            )
        )

    def wait_for_completion(
        self,
        batch_id: str,
        *,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float | None = None,
        on_progress: Callable[[BatchStatus], Any] | None = None,
        options: RequestOptions | None = None,
    ) -> BatchStatus:
        """Polls until the batch is ``completed`` or ``cancelled``, then returns its final status.

        Raises ``APITimeoutError`` if ``timeout`` seconds pass first. Waits indefinitely by default.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            batch = self.get(batch_id, options=options)
            if on_progress is not None:
                on_progress(batch)
            if batch["status"] in ("completed", "cancelled"):
                return batch

            wait = poll_interval
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise APITimeoutError(
                        f"Batch {batch_id} did not finish within {timeout} seconds"
                    )
                wait = min(poll_interval, remaining)
            _http.sleep(wait)
