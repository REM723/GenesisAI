"use client";

import { cn } from "@/lib/utils";
import { Spinner } from "./ui/spinner";
import type { RunEvent } from "@/lib/run-stream";

const STEPS = [
  { k: "product_manager", label: "Product Manager", d: "Structures requirements and scope" },
  { k: "architect", label: "Architect", d: "Designs the stack and task list" },
  { k: "backend", label: "Backend", d: "Writes API code, models, migrations" },
  { k: "frontend", label: "Frontend", d: "Builds pages, components, styling" },
  { k: "qa", label: "QA", d: "Generates tests and a defect report" },
  { k: "devops", label: "DevOps", d: "Dockerfile, CI, deployment guide" },
  { k: "documentation", label: "Documentation", d: "README, API docs, setup guide" },
] as const;

type State = "pending" | "active" | "done" | "failed";

function Node({ state }: { state: State }) {
  if (state === "active") return <Spinner className="h-[18px] w-[18px]" />;
  return (
    <span
      className={cn(
        "grid h-[18px] w-[18px] place-items-center rounded-full border transition-colors duration-200 ease-out",
        state === "done" && "border-ok/40 bg-ok/15 text-ok",
        state === "failed" && "border-err/40 bg-err/15 text-err",
        state === "pending" && "border-line/15 bg-surface",
      )}
    >
      {state === "done" ? (
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden>
          <path
            d="M1.5 5.2 4 7.5 8.5 2.5"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ) : state === "failed" ? (
        <span className="h-[3px] w-[3px] rounded-full bg-err" />
      ) : null}
    </span>
  );
}

export function RunTimeline({ events }: { events: RunEvent[] }) {
  const started = new Set(events.filter((e) => e.type === "start").map((e) => e.agent));
  const completed = new Set(events.filter((e) => e.type === "complete").map((e) => e.agent));
  const failedAt = events.find((e) => e.type === "timeout")?.agent;

  return (
    <ol className="relative space-y-1">
      <span className="absolute left-[8.5px] top-3 bottom-3 w-px bg-line/10" aria-hidden />
      {STEPS.map((step) => {
        const state: State = completed.has(step.k)
          ? "done"
          : failedAt === step.k
            ? "failed"
            : started.has(step.k)
              ? "active"
              : "pending";
        return (
          <li key={step.k} className="relative flex items-center gap-3.5 py-2">
            <span className="relative z-10 bg-bg">
              <Node state={state} />
            </span>
            <div className="flex-1">
              <p
                className={cn(
                  "text-sm transition-colors duration-200 ease-out",
                  state === "pending" ? "text-faint" : "text-ink",
                )}
              >
                {step.label}
              </p>
              <p className="text-xs text-faint">{step.d}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
