import { cn } from "@/lib/utils";

// Muted, legible status treatment. No emoji, quiet dots, sentence-case labels.
const MAP: Record<string, { label: string; dot: string; text: string }> = {
  draft: { label: "Draft", dot: "bg-faint", text: "text-muted" },
  queued: { label: "Queued", dot: "bg-faint", text: "text-muted" },
  analyzing: { label: "Analyzing", dot: "bg-warn", text: "text-warn" },
  running: { label: "Running", dot: "bg-warn", text: "text-warn" },
  completed: { label: "Completed", dot: "bg-ok", text: "text-ok" },
  succeeded: { label: "Succeeded", dot: "bg-ok", text: "text-ok" },
  failed: { label: "Failed", dot: "bg-err", text: "text-err" },
  timeout: { label: "Timed out", dot: "bg-err", text: "text-err" },
};

export function StatusBadge({ status }: { status: string }) {
  const s = MAP[status] ?? { label: status, dot: "bg-faint", text: "text-muted" };
  const pulse = status === "running" || status === "analyzing";
  return (
    <span className="inline-flex items-center gap-2 text-[13px]">
      <span className="relative flex h-1.5 w-1.5">
        {pulse ? (
          <span
            className={cn(
              "absolute inline-flex h-full w-full animate-ping rounded-full opacity-60",
              s.dot,
            )}
          />
        ) : null}
        <span className={cn("relative inline-flex h-1.5 w-1.5 rounded-full", s.dot)} />
      </span>
      <span className={s.text}>{s.label}</span>
    </span>
  );
}
