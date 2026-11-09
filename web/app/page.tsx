import { HealthPanel } from "@/components/health-panel";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-6 px-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">NexusRAG</h1>
        <p className="text-sm text-muted-foreground">
          Your local second brain. Everything stays on this machine.
        </p>
      </header>
      <section aria-labelledby="health-heading" className="space-y-3">
        <h2
          id="health-heading"
          className="text-sm font-medium uppercase tracking-wide"
        >
          System
        </h2>
        <HealthPanel />
      </section>
    </main>
  );
}
