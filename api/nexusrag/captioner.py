from __future__ import annotations

import base64
from pathlib import Path

from nexusrag import providers
from nexusrag.providers import ProviderConfig

MEDIA_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}

CAPTION_SYSTEM = (
    "You describe images so they can be found by search later. "
    "Transcribe any visible text, numbers and chart values. Describe layout and what the image shows. "
    "Be factual and concise. Do not guess at anything you cannot see."
)


def media_type_for(path: Path) -> str:
    return MEDIA_TYPES.get(path.suffix.lower(), "image/png")


def image_block(path: Path) -> dict:
    return {
        "type": "image",
        "media_type": media_type_for(path),
        "data": base64.b64encode(path.read_bytes()).decode("ascii"),
    }


def caption_image(config: ProviderConfig, path: Path) -> str:
    """One vision call. Raises ProviderError (message is key-free)."""
    content = [image_block(path), {"type": "text", "text": "Describe this image for search."}]
    return providers.complete(config, CAPTION_SYSTEM, content, max_tokens=500).strip()
