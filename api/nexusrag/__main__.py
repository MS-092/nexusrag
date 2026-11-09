"""Run with: uv run python -m nexusrag  (always binds to loopback)."""
import uvicorn

HOST = "127.0.0.1"
PORT = 8000

if __name__ == "__main__":
    uvicorn.run("nexusrag.main:app", host=HOST, port=PORT)
