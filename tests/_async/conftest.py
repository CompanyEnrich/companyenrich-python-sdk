from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def delays(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Replaces real waits and records how long the SDK would have slept."""
    recorded: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        recorded.append(seconds)

    monkeypatch.setattr("companyenrich._async._http.sleep", fake_sleep)
    return recorded
