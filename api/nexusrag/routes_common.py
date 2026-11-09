from __future__ import annotations

from fastapi import HTTPException, Request

from nexusrag.providers import ProviderConfig, ProviderConfigError, build_config


def provider_config(request: Request) -> ProviderConfig | None:
    """Read the per-request provider headers. The key lives only in this request."""
    h = request.headers
    try:
        return build_config(
            h.get("x-provider"), h.get("x-provider-model"), h.get("x-provider-key"), h.get("x-provider-base-url")
        )
    except ProviderConfigError as exc:
        raise HTTPException(400, str(exc)) from None
