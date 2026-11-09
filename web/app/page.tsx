import { AppShell } from "@/components/app-shell";
import { HealthPanel } from "@/components/health-panel";

export default function Home() {
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-3xl flex-col gap-10 px-6 py-12">
      <header className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-[-0.02em]">NexusRAG</h1>
        <p className="text-sm text-muted-foreground">
          Your local second brain. Everything stays on this machine.
        </p>
      </header>
      <main className="flex-1">
        <AppShell />
      </main>
      <footer
        aria-labelledby="health-heading"
        className="space-y-3 border-t border-border pt-6"
      >
        <h2
          id="health-heading"
          className="text-xs font-medium tracking-wide text-muted-foreground uppercase"
        >
          System
        </h2>
        <HealthPanel />
      </footer>
    </div>
  );
}
