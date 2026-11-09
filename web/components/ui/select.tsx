import { ChevronDown } from "lucide-react";
import { cn } from "cn";

// One select for the whole app: same height as inputs and buttons (h-9),
// native arrow replaced by a chevron pinned to the vertical centre.
function Select({
  className,
  children,
  ...props
}: React.ComponentProps<"select">) {
  return (
    <span className={cn("relative inline-flex h-9 min-w-0", className)}>
      <select
        data-slot="select"
        className="h-full w-full min-w-0 appearance-none rounded-lg border border-border bg-background pr-9 pl-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
        {...props}
      >
        {children}
      </select>
      <ChevronDown
        aria-hidden
        className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-muted-foreground"
      />
    </span>
  );
}

export { Select };
