# NexusRAG web

Next.js (App Router) front end for NexusRAG. See the [root README](../README.md) for what the project does.

```bash
bun install
bun run dev        # http://localhost:3000 (needs the API on 127.0.0.1:8000)
bun test           # unit tests
bun run typecheck && bun run lint
bun run e2e        # Playwright smoke test (starts the API and a fake provider)
```

`NEXT_PUBLIC_API_URL` overrides the API address (default `http://127.0.0.1:8000`).
