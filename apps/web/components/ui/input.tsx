import { forwardRef } from "react";

import { cn } from "@/lib/utils";

const field =
  "w-full rounded-[10px] border border-line/12 bg-surface/70 px-3.5 text-ink placeholder:text-faint " +
  "transition-colors duration-150 ease-out hover:border-line/20 focus:border-accent/50";

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return <input ref={ref} className={cn(field, "h-10 text-sm", className)} {...props} />;
  },
);

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className, ...props }, ref) {
  return (
    <textarea
      ref={ref}
      className={cn(field, "min-h-28 resize-none py-3 text-sm leading-relaxed", className)}
      {...props}
    />
  );
});

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block space-y-2">
      <span className="text-[13px] font-medium text-muted">{label}</span>
      {children}
      {hint ? <span className="block text-xs text-faint">{hint}</span> : null}
    </label>
  );
}
