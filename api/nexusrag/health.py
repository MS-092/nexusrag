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


def health_report(data_dir: Path) -> dict:
    storage = storage_status(data_dir)
    return {
        "status": "ok" if storage["status"] == "ok" else "degraded",
        # Reported honestly: these components arrive in later tickets.
        "embedder": {"status": "not_initialized"},
        "index": {"status": "not_initialized"},
        "storage": storage,
    }
