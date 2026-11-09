from __future__ import annotations

from pathlib import Path


def storage_status(data_dir: Path) -> dict:
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        probe = data_dir / ".write-probe"
        probe.write_text("ok")
        probe.unlink()
        return {"status": "ok"}
    except OSError as exc:
        return {"status": "error", "detail": exc.strerror or "storage not writable"}


def health_report(data_dir: Path, embedder=None, index=None) -> dict:
    storage = storage_status(data_dir)
    index_status = {"status": "not_initialized"}
    if index is not None:
        try:
            index.client.collection_exists("brain")
            index_status = {"status": "ok"}
        except Exception as exc:  # noqa: BLE001 - report, don't crash health
            index_status = {"status": "error", "detail": type(exc).__name__}
    embedder_status = {"status": "not_initialized"}
    if embedder is not None:
        # Models load lazily on first use, so "not_loaded" is normal at startup.
        embedder_status = {"status": "ready" if embedder.loaded else "not_loaded"}
    ok = storage["status"] == "ok" and index_status["status"] in ("ok", "not_initialized")
    return {
        "status": "ok" if ok else "degraded",
        "embedder": embedder_status,
        "index": index_status,
        "storage": storage,
    }
