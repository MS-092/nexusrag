# NexusRAG

Local-first second brain. Collect PDFs, images, spreadsheets and Markdown notes in one place, organise them into notebooks, and chat with them through your own AI provider (bring your own key). Everything runs on your machine.

Status: in development.

## Highlights

- Text-grounded hybrid RAG: every file is turned into text once at ingestion (extraction, local OCR, optional vision caption), then retrieved with one local text embedder plus keyword search, so answers about charts and tables cite real text.
- Offline, hash-cached ingestion: re-uploading a file never reprocesses it.
- Stateless BYOK: your API key stays in your browser and is sent per request; the server never stores or logs it.
- Notebooks fill themselves from rules and accept manual pins; private sources never reach any AI provider.
- Chat skills such as `/summarize` and `/status`.

## Stack

- `api/`: Python, uv, FastAPI, Qdrant (embedded), SQLite
- `web/`: Next.js, bun, Tailwind, shadcn/ui
- `skills/`: one Markdown file per skill

## Providers

Anthropic, OpenAI, and any OpenAI-compatible endpoint (Ollama, OpenRouter, OpenCode).
