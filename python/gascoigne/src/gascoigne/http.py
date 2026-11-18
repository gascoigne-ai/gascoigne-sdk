"""HTTP adapter: the client of the gascoigne server's `/sdk/v1` routes (spec/protocol.md)."""

from __future__ import annotations

from typing import Any

import httpx

from gascoigne.models import OptimizeRequest, Result


def health(base_url: str) -> int | None:
    """The protocol version the server reports, or None when it does not answer."""
    try:
        response = httpx.get(f"{base_url}/sdk/v1/health", timeout=0.5)
        if response.status_code != 200:
            return None
        proto = response.json().get("proto")
    except (httpx.HTTPError, ValueError):
        return None
    return proto if isinstance(proto, int) else -1


class ServerClient:
    """Typed calls to the server. Every method raises on failure; the caller absorbs it."""

    def __init__(self, base_url: str, timeout: float) -> None:
        self._http = httpx.Client(base_url=base_url, timeout=timeout)

    def optimize(self, request: OptimizeRequest) -> Result:
        response = self._http.post("/sdk/v1/optimize", json=request.to_json())
        response.raise_for_status()
        return Result.from_json(response.json())

    def raw(self, raw_id: str) -> str:
        response = self._http.get(f"/sdk/v1/raw/{raw_id}")
        response.raise_for_status()
        return response.text

    def get_json(self, path: str, query: dict[str, str]) -> Any:
        """GET a ledger route and decode its JSON body."""
        response = self._http.get(path, params=query)
        response.raise_for_status()
        return response.json()
