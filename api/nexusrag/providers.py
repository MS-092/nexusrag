"""Provider gateway (BYOK). Builds one stateless request per call from the
caller's provider, base URL, model and key. Nothing here stores or logs a key."""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

PROVIDERS = ("anthropic", "openai", "openai-compatible")
DEFAULT_MODELS = {"anthropic": "claude-haiku-4-5", "openai": "gpt-4o-mini"}
DEFAULT_BASES = {"anthropic": "https://api.anthropic.com", "openai": "https://api.openai.com"}
ANTHROPIC_VERSION = "2023-06-01"


class ProviderError(Exception):
    """A failure that is safe to show the user: it never contains the key."""

    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


class ProviderConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    model: str
    api_key: str | None = None
    base_url: str | None = None

    def __repr__(self) -> str:  # never print the key
        return f"ProviderConfig(provider={self.provider!r}, model={self.model!r}, base_url={self.base_url!r})"


def build_config(provider: str | None, model: str | None, key: str | None, base_url: str | None) -> ProviderConfig | None:
    """Validate request headers. Returns None when the caller supplied no provider."""
    if not provider:
        return None
    provider = provider.strip().lower()
    if provider not in PROVIDERS:
        raise ProviderConfigError(f"Unknown provider. Choose one of: {', '.join(PROVIDERS)}.")
    key = (key or "").strip() or None
    if provider in ("anthropic", "openai") and not key:
        raise ProviderConfigError(f"An API key is required for {provider}.")
    model = (model or "").strip() or DEFAULT_MODELS.get(provider)
    if not model:
        raise ProviderConfigError("A model name is required for openai-compatible providers.")
    base = (base_url or "").strip().rstrip("/") or DEFAULT_BASES.get(provider)
    if provider == "openai-compatible" and not base:
        raise ProviderConfigError("A base URL is required for openai-compatible providers.")
    if base and base.endswith("/v1"):
        base = base[: -len("/v1")]
    return ProviderConfig(provider=provider, model=model, api_key=key, base_url=base)


def _host(base: str | None) -> str:
    return urlparse(base or "").netloc or "the provider"


Content = str | list[dict]  # blocks: {"type":"text","text"} | {"type":"image","media_type","data"}


def _wire(provider: str, content: Content) -> str | list[dict]:
    """Convert NexusRAG's neutral content blocks to the provider's wire format."""
    if isinstance(content, str):
        return content
    out: list[dict] = []
    for block in content:
        if block["type"] == "text":
            out.append({"type": "text", "text": block["text"]})
        elif provider == "anthropic":
            out.append(
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": block["media_type"], "data": block["data"]},
                }
            )
        else:
            out.append(
                {"type": "image_url", "image_url": {"url": f"data:{block['media_type']};base64,{block['data']}"}}
            )
    return out


def complete(config: ProviderConfig, system: str, user_content: Content, max_tokens: int = 700) -> str:
    """One chat completion. Raises ProviderError with a user-safe message."""
    assert config.base_url
    user_content = _wire(config.provider, user_content)
    try:
        if config.provider == "anthropic":
            res = httpx.post(
                f"{config.base_url}/v1/messages",
                headers={"x-api-key": config.api_key or "", "anthropic-version": ANTHROPIC_VERSION},
                json={
                    "model": config.model,
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": [{"role": "user", "content": user_content}],
                },
                timeout=60,
            )
        else:
            headers = {"Authorization": f"Bearer {config.api_key}"} if config.api_key else {}
            res = httpx.post(
                f"{config.base_url}/v1/chat/completions",
                headers=headers,
                json={
                    "model": config.model,
                    "max_tokens": max_tokens,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_content},
                    ],
                },
                timeout=60,
            )
    except httpx.HTTPError as exc:
        raise ProviderError(f"Cannot reach the provider at {_host(config.base_url)}.", 502) from None

    if res.status_code in (401, 403):
        raise ProviderError("The provider rejected the API key.", 401)
    if res.status_code >= 400:
        raise ProviderError(f"The provider returned an error (HTTP {res.status_code}).", 502)
    try:
        data = res.json()
        if config.provider == "anthropic":
            return "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError, ValueError):
        raise ProviderError("The provider sent a reply NexusRAG could not read.", 502) from None
