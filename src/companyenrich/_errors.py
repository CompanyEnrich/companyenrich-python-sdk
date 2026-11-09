from __future__ import annotations

from typing import Any

import httpx


class CompanyEnrichError(Exception):
    """Base class for every error raised by this SDK."""


class APIConnectionError(CompanyEnrichError):
    """The request never produced a response, for example because of a DNS or socket failure."""


class APITimeoutError(CompanyEnrichError):
    """The request, or a ``batches.wait_for_completion`` call, ran out of time."""


class APIError(CompanyEnrichError):
    """The API responded with a non-2xx status."""

    def __init__(self, status: int, headers: httpx.Headers, body: Any) -> None:
        problem: dict[str, Any] = body if isinstance(body, dict) else {}
        super().__init__(_format_message(status, problem))
        self.status = status
        self.headers = headers
        #: The parsed response body, or the raw text if it was not JSON.
        self.body = body
        self.type: str | None = problem.get("type")
        self.title: str | None = problem.get("title")
        self.detail: str | None = problem.get("detail")
        self.instance: str | None = problem.get("instance")
        #: Field-level validation messages, keyed by field name.
        self.errors: dict[str, list[str]] | None = problem.get("errors")
        #: Value of the ``x-trace-id`` response header. Include it in support requests.
        self.trace_id: str | None = headers.get("x-trace-id")


class BadRequestError(APIError):
    """``400``: the request was malformed."""


class AuthenticationError(APIError):
    """``401``: the API key is missing or invalid."""


class PaymentRequiredError(APIError):
    """``402``: the account is out of credits or its plan does not include this request."""


class PermissionDeniedError(APIError):
    """``403``: the API key may not perform this request."""


class NotFoundError(APIError):
    """``404``: the company, person, or batch does not exist."""


class ValidationError(APIError):
    """``422``: the request failed validation. See ``errors``."""


class RateLimitError(APIError):
    """``429``: a rate limit was exceeded and automatic retries did not resolve it."""


class ServerError(APIError):
    """``5xx``: the API failed to process the request."""


_ERRORS_BY_STATUS: dict[int, type[APIError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    402: PaymentRequiredError,
    403: PermissionDeniedError,
    404: NotFoundError,
    422: ValidationError,
    429: RateLimitError,
}


def create_api_error(status: int, headers: httpx.Headers, body: Any) -> APIError:
    fallback = ServerError if status >= 500 else APIError
    return _ERRORS_BY_STATUS.get(status, fallback)(status, headers, body)


def _format_message(status: int, problem: dict[str, Any]) -> str:
    summary = ": ".join(part for part in (problem.get("title"), problem.get("detail")) if part)
    fields = "; ".join(
        f"{field}: {', '.join(messages)}"
        for field, messages in (problem.get("errors") or {}).items()
    )
    return " ".join(part for part in (str(status), summary, fields and f"({fields})") if part)
