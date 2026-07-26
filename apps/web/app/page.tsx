import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Wordmark } from "@/components/wordmark";

const STEPS = [
  { n: "01", t: "Describe the idea", d: "One paragraph of plain English is enough to begin." },
  { n: "02", t: "Watch the team work", d: "Specialised agents plan, build, review, and document." },
  {
    n: "03",
    t: "Export the repository",
    d: "A standalone project with code, tests, and a README.",
  },
];

export default function Landing() {
  return (
    <main className="grain relative min-h-screen">
      <div className="mx-auto max-w-5xl px-6">
        <header className="flex h-14 items-center justify-between">
          <Wordmark />
          <div className="flex items-center gap-2">
            <Link href="/login">
              <Button variant="ghost" size="sm">
                Sign in
              </Button>
            </Link>
            <Link href="/signup">
              <Button size="sm">Get started</Button>
            </Link>
          </div>
        </header>

        <section className="settle pb-24 pt-24 sm:pt-32">
          <p className="mb-6 text-[13px] uppercase tracking-[0.2em] text-faint">
            An AI engineering team
          </p>
          <h1 className="max-w-3xl text-balance font-serif text-5xl leading-[1.05] tracking-tightest text-ink sm:text-6xl">
            From a product idea to production ready software.
          </h1>
          <p className="mt-7 max-w-xl text-lg leading-relaxed text-muted">
            GenesisAI reads your idea, plans an architecture, writes the code, tests it, and
            packages a repository you can run anywhere. Not a prompt. A finished project.
          </p>
          <div className="mt-10 flex items-center gap-3">
            <Link href="/signup">
              <Button size="lg">Start a project</Button>
            </Link>
            <Link href="/login">
              <Button size="lg" variant="outline">
                Sign in
              </Button>
            </Link>
          </div>
        </section>

        <section className="grid gap-px overflow-hidden rounded-[var(--radius)] border border-line/10 bg-line/10 sm:grid-cols-3">
          {STEPS.map((s) => (
            <div key={s.n} className="bg-bg p-7">
              <span className="font-mono text-xs text-accent">{s.n}</span>
              <h3 className="mt-4 text-[15px] font-medium text-ink">{s.t}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{s.d}</p>
            </div>
          ))}
        </section>

        <footer className="border-t border-line/8 py-8 text-center text-xs text-faint">
          Built for founders, developers, and teams who want the finished thing.
        </footer>
      </div>
    </main>
  );
}
