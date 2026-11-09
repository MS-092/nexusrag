/** A fake AI provider for the smoke test. Speaks the OpenAI-compatible chat API,
 *  records every request, and exposes them at /__requests for assertions. */
const received: {
  path: string;
  headers: Record<string, string>;
  body: string;
}[] = [];

Bun.serve({
  port: Number(process.env.FAKE_PROVIDER_PORT ?? 4010),
  hostname: "127.0.0.1",
  async fetch(req) {
    const url = new URL(req.url);
    if (url.pathname === "/__requests") return Response.json(received);
    if (req.method === "POST") {
      received.push({
        path: url.pathname,
        headers: Object.fromEntries(req.headers.entries()),
        body: await req.text(),
      });
      return Response.json({
        choices: [
          {
            message: {
              role: "assistant",
              content: "Revenue in Q3 was 4.2 million dollars [1].",
            },
          },
        ],
      });
    }
    return new Response("ok");
  },
});
console.log("fake provider ready");
