"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { StatusBadge } from "@/components/status-badge";
import { api, type Project } from "@/lib/api";
import { useAuth } from "@/lib/auth";

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

export default function Dashboard() {
  const { token } = useAuth();
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    api
      .listProjects(token)
      .then((page) => setProjects(page.items))
      .catch((e) => setError(e.message));
  }, [token]);

  return (
    <div>
      <div className="flex items-end justify-between">
        <div>
          <h1 className="font-serif text-3xl tracking-tight text-ink">Projects</h1>
          <p className="mt-1.5 text-sm text-muted">Every idea you have handed to the team.</p>
        </div>
        <Link href="/projects/new">
          <Button>New project</Button>
        </Link>
      </div>

      <div className="mt-8">
        {error ? (
          <Card className="p-6 text-sm text-err">{error}</Card>
        ) : projects === null ? (
          <div className="flex items-center gap-3 py-16 text-sm text-muted">
            <Spinner /> Loading your projects
          </div>
        ) : projects.length === 0 ? (
          <Card className="flex flex-col items-center justify-center gap-4 px-6 py-20 text-center">
            <p className="max-w-xs text-balance text-muted">
              No projects yet. Describe an idea and the team will take it from there.
            </p>
            <Link href="/projects/new">
              <Button>Create your first project</Button>
            </Link>
          </Card>
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2">
            {projects.map((p, i) => (
              <li key={p.id} className="rise" style={{ animationDelay: `${i * 45}ms` }}>
                <Link href={`/projects/${p.id}`}>
                  <Card className="group h-full p-5 transition-colors duration-150 ease-out hover:border-line/20 hover:bg-surface2">
                    <div className="flex items-start justify-between gap-3">
                      <h3 className="text-[15px] font-medium text-ink">{p.name}</h3>
                      <StatusBadge status={p.status} />
                    </div>
                    <p className="mt-6 text-xs text-faint">Updated {timeAgo(p.created_at)}</p>
                  </Card>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
