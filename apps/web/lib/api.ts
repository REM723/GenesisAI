// Hand-written typed client for the GenesisAI API. Generating this from the backend OpenAPI
// is the eventual upgrade; for the MVP the surface is small enough to keep by hand.

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Tokens = { access_token: string; refresh_token: string; token_type: string };
export type User = { id: string; email: string; role: string; created_at: string };

export type Project = { id: string; name: string; status: string; created_at: string };
export type ProjectPage = { items: Project[]; next_cursor: string | null };
export type ArtifactRef = {
  id: string;
  path: string | null;
  type: string | null;
  language: string | null;
  version: number;
};
export type RunSummary = { id: string; status: string; current_agent: string | null };
export type ProjectDetail = Project & {
  idea: string;
  code: ArtifactRef[];
  documents: ArtifactRef[];
  latest_run: RunSummary | null;
};

export type PromptVersion = { version: number; score: number | null };
export type Prompt = {
  id: string;
  type: string;
  content: string;
  score: number | null;
  versions: PromptVersion[];
};
export type ApiKey = { id: string; provider: string; created_at: string };
export type RunAccepted = { run_id: string; status: string };

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function parse<T>(res: Response): Promise<T> {
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail =
      typeof body?.detail === "string"
        ? body.detail
        : Array.isArray(body?.detail)
          ? body.detail.map((d: { msg?: string }) => d.msg).join(", ")
          : `Request failed (${res.status})`;
    throw new ApiError(res.status, detail);
  }
  return body as T;
}

function headers(token?: string): HeadersInit {
  const h: HeadersInit = { "Content-Type": "application/json" };
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

export const api = {
  base: BASE,

  register: (email: string, password: string) =>
    fetch(`${BASE}/auth/register`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ email, password }),
    }).then(parse<User>),

  login: (email: string, password: string) =>
    fetch(`${BASE}/auth/login`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ email, password }),
    }).then(parse<Tokens>),

  refresh: (refresh_token: string) =>
    fetch(`${BASE}/auth/refresh`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ refresh_token }),
    }).then(parse<Tokens>),

  listProjects: (token: string, cursor?: string) =>
    fetch(`${BASE}/projects${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ""}`, {
      headers: headers(token),
    }).then(parse<ProjectPage>),

  createProject: (token: string, name: string, idea: string) =>
    fetch(`${BASE}/projects`, {
      method: "POST",
      headers: headers(token),
      body: JSON.stringify({ name, idea }),
    }).then(parse<Project>),

  getProject: (token: string, id: string) =>
    fetch(`${BASE}/projects/${id}`, { headers: headers(token) }).then(parse<ProjectDetail>),

  generatePrompts: (token: string, project_id: string) =>
    fetch(`${BASE}/prompts/generate`, {
      method: "POST",
      headers: headers(token),
      body: JSON.stringify({ project_id }),
    }).then(parse<Prompt>),

  startRun: (token: string, project_id: string) =>
    fetch(`${BASE}/agents/run`, {
      method: "POST",
      headers: headers(token),
      body: JSON.stringify({ project_id }),
    }).then(parse<RunAccepted>),

  listKeys: (token: string) =>
    fetch(`${BASE}/keys`, { headers: headers(token) }).then(parse<ApiKey[]>),

  addKey: (token: string, provider: string, key: string) =>
    fetch(`${BASE}/keys`, {
      method: "POST",
      headers: headers(token),
      body: JSON.stringify({ provider, key }),
    }).then(parse<ApiKey>),

  streamUrl: (run_id: string) => `${BASE}/agents/runs/${run_id}/stream`,

  exportProject: async (token: string, project_id: string): Promise<Blob> => {
    const res = await fetch(`${BASE}/exports/${project_id}`, { headers: headers(token) });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(
        res.status,
        typeof body?.detail === "string" ? body.detail : `Export failed (${res.status})`,
      );
    }
    return res.blob();
  },
};
