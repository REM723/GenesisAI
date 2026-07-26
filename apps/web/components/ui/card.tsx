import { cn } from "@/lib/utils";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius)] border border-line/10 bg-surface/60 shadow-soft",
        className,
      )}
      {...props}
    />
  );
}
