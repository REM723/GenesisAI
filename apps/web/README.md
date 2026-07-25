# apps/web — GenesisAI frontend

Next.js (App Router) + React + TypeScript + Tailwind + shadcn/ui. Server Components by
default. Phase 0 ships a placeholder landing page; the client is built in Phase 7.

## Run

```bash
pnpm install          # from repo root
pnpm --filter web dev # http://localhost:3000
```

## Checks

```bash
pnpm --filter web lint
pnpm --filter web exec tsc --noEmit
```
