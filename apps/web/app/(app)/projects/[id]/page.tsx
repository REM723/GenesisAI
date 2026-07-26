"use client";

import { useCallback, useEffect, useState } from "react";

import { RunTimeline } from "@/components/run-timeline";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { api, type Prompt, type ProjectDetail } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useRunStream } from "@/lib/run-stream";

function Section({
  title,
  aside,
  children,
}: {
  title: string;
  aside?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="settle">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-[13px] font-medium uppercase tracking-[0.14em] text-faint">{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  );
}

export default function ProjectPage({ params }: { params: { id: string } }) {
  const { token } = useAuth();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [prompt, setPrompt] = useState<Prompt | null>(null);
  const [promptBusy, setPromptBusy] = useState(false);

  const [runId, setRunId] = useState<string | null>(null);
  const [runBusy, setRunBusy] = useState(false);
  const { events, finished } = useRunStream(runId, token);

  const [exportBusy, setExportBusy] = useState(false);
  const [exportErr, setExportErr] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!token) return;
    api
      .getProject(token, params.id)
      .then(setProject)
      .catch((e) => setError(e.message));
  }, [token, params.id]);

  useEffect(load, [load]);
  useEffect(() => {
    if (finished) load();
  }, [finished, load]);

  async function generate() {
    if (!token) return;
    setPromptBusy(true);
    try {
      setPrompt(await api.generatePrompts(token, params.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not generate the prompt.");
    } finally {
      setPromptBusy(false);
    }
  }

  async function exportZip() {
    if (!token || !project) return;
    setExportBusy(true);
    setExportErr(null);
    try {
      const blob = await api.exportProject(token, params.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${project.name}.zip`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setExportErr(e instanceof Error ? e.message : "Export failed.");
    } finally {
      setExportBusy(false);
    }
  }

  async function run() {
    if (!token) return;
    setRunBusy(true);
    try {
      const accepted = await api.startRun(token, params.id);
      setRunId(accepted.run_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start the run.");
    } finally {
      setRunBusy(false);
    }
  }

  if (error) return <Card className="p-6 text-sm text-err">{error}</Card>;
  if (!project)
    return (
      <div className="flex items-center gap-3 py-16 text-sm text-muted">
        <Spinner /> Loading project
      </div>
    );

  const running = runId !== null && finished === null;

  return (
    <div className="space-y-10">
      <header className="settle">
        <div className="flex items-center gap-3">
          <h1 className="font-serif text-3xl tracking-tight text-ink">{project.name}</h1>
          <StatusBadge status={project.latest_run?.status ?? project.status} />
        </div>
        <p className="mt-3 max-w-2xl leading-relaxed text-muted">{project.idea}</p>
      </header>

      <Section
        title="Optimized prompt"
        aside={
          <Button size="sm" variant="outline" onClick={generate} disabled={promptBusy}>
            {promptBusy ? <Spinner /> : prompt ? "Regenerate" : "Generate prompt"}
          </Button>
        }
      >
        {prompt ? (
          <Card className="overflow-hidden">
            <div className="flex items-center justify-between border-b border-line/8 px-5 py-3">
              <span className="text-[13px] text-muted">
                Quality score
                <span className="ml-2 font-mono text-ink">
                  {prompt.score !== null ? prompt.score.toFixed(2) : "n/a"}
                </span>
              </span>
              <span className="text-xs text-faint">
                {prompt.versions.length} refinement{prompt.versions.length === 1 ? "" : "s"}
              </span>
            </div>
            <pre className="max-h-72 overflow-auto whitespace-pre-wrap px-5 py-4 font-mono text-[12.5px] leading-relaxed text-muted">
              {prompt.content}
            </pre>
          </Card>
        ) : (
          <Card className="px-5 py-8 text-center text-sm text-muted">
            Turn the idea into a scored, model-aware prompt before running the team.
          </Card>
        )}
      </Section>

      <Section
        title="The build"
        aside={
          <Button size="sm" onClick={run} disabled={runBusy || running}>
            {runBusy || running ? <Spinner /> : "Run the team"}
          </Button>
        }
      >
        <Card className="p-6">
          {runId === null ? (
            <p className="py-4 text-center text-sm text-muted">
              When you are ready, hand the project to the agents and watch it come together.
            </p>
          ) : (
            <>
              <RunTimeline events={events} />
              {finished ? (
                <p className="mt-4 border-t border-line/8 pt-4 text-[13px]">
                  <StatusBadge status={finished} />
                </p>
              ) : null}
            </>
          )}
        </Card>
      </Section>

      {project.code.length || project.documents.length ? (
        <Section title="Artifacts">
          <Card className="divide-y divide-line/8">
            {[...project.code, ...project.documents].map((a) => (
              <div key={a.id} className="flex items-center justify-between px-5 py-3">
                <span className="font-mono text-[13px] text-ink">
                  {a.path ?? a.type ?? "artifact"}
                </span>
                <span className="text-xs text-faint">
                  {a.language ?? "doc"} · v{a.version}
                </span>
              </div>
            ))}
          </Card>
        </Section>
      ) : null}

      <Section title="Export">
        <Card className="flex items-center justify-between px-5 py-4">
          <p className="text-sm text-muted">
            {exportErr ?? "Download the finished project as a standalone repository."}
          </p>
          <Button variant="outline" size="sm" onClick={exportZip} disabled={exportBusy}>
            {exportBusy ? <Spinner /> : "Export .zip"}
          </Button>
        </Card>
      </Section>
    </div>
  );
}
