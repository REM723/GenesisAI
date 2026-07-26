import { cn } from "@/lib/utils";

// A brisk spinner reads as faster loading. 640ms linear, thin ring.
export function Spinner({ className }: { className?: string }) {
  return (
    <span
      role="status"
      aria-label="Loading"
      className={cn(
        "inline-block h-4 w-4 animate-spin rounded-full border-[1.5px] border-line/20 border-t-ink/80",
        className,
      )}
      style={{ animationDuration: "640ms" }}
    />
  );
}
