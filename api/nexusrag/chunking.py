from __future__ import annotations

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200


def chunk_blocks(blocks: list[dict], size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """Split blocks into chunks. Short blocks stay whole; long ones are windowed
    with overlap. Every chunk keeps its block's position for Citations."""
    chunks: list[dict] = []
    for block in blocks:
        text = block["text"]
        if len(text) <= size:
            chunks.append({"text": text, "position": block["position"]})
            continue
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            chunks.append({"text": text[start:end], "position": block["position"]})
            if end == len(text):
                break
            start = end - overlap
    return chunks
