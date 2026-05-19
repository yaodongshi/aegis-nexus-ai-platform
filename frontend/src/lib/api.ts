const BASE = '/api/v1';

function getToken(): string | null {
  return localStorage.getItem('tap_token');
}

export function setToken(token: string): void {
  localStorage.setItem('tap_token', token);
}

export function clearToken(): void {
  localStorage.removeItem('tap_token');
}

function isAuthExpired(status: number, detail: string): boolean {
  if (status !== 401) return false;
  const text = (detail || '').toLowerCase();
  return (
    text.includes('token expired')
    || text.includes('invalid token')
    || text.includes('user not found')
    || text.includes('missing bearer token')
    || text.includes('unauthorized')
  );
}

function handleAuthExpiry(status: number, detail: string): void {
  if (!isAuthExpired(status, detail)) return;
  clearToken();
  if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
    window.location.assign('/login');
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${BASE}${path}`, { ...options, headers });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    handleAuthExpiry(resp.status, String(err.detail ?? resp.statusText));
    throw new Error(err.detail ?? resp.statusText);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json();
}

const get = <T>(path: string) => request<T>(path);
const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: JSON.stringify(body) });
const put = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: 'PUT', body: JSON.stringify(body) });
const del = <T>(path: string) => request<T>(path, { method: 'DELETE' });

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (username: string, email: string, password: string) =>
    post('/users/register', { username, email, password }),
  login: (identity: string, password: string) =>
    post<{ access_token: string; user: { id: string; username: string; email: string } }>(
      '/users/login', { identity, password }
    ),
  me: () => get<{ id: string; username: string; email: string; role: string }>('/users/me'),
  resetPassword: (old_password: string, new_password: string) =>
    post('/users/reset-password', { old_password, new_password }),
};

export const usersAdminApi = {
  list: () => get<any[]>('/users/admin/list'),
  create: (data: { username: string; email: string; password: string; role?: string }) =>
    post<any>('/users/admin/create', data),
  update: (userId: string, data: { username?: string; email?: string; role?: string }) =>
    request<any>(`/users/admin/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  updateStatus: (userId: string, is_active: boolean) =>
    request<any>(`/users/admin/${userId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ is_active }),
    }),
  resetPassword: (userId: string, new_password: string) =>
    post<any>(`/users/admin/${userId}/reset_password`, { new_password }),
};

// ── Teams ─────────────────────────────────────────────────────────────────────
export const teamsApi = {
  list: () => get<any[]>('/teams/'),
  create: (name: string, description: string) => post<any>('/teams/', { name, description }),
  get: (id: string) => get<any>(`/teams/${id}`),
  invite: (teamId: string, username: string, role: string) =>
    post<any>(`/teams/${teamId}/members`, { username, role }),
  removeMember: (teamId: string, userId: string) =>
    del(`/teams/${teamId}/members/${userId}`),
};

// ── Projects ──────────────────────────────────────────────────────────────────
export const projectsApi = {
  list: () => get<any[]>('/projects/'),
  create: (name: string, team_id: string, description: string) =>
    post<any>('/projects/', { name, team_id, description }),
  get: (id: string) => get<any>(`/projects/${id}`),
};

// ── Repos ─────────────────────────────────────────────────────────────────────
export const reposApi = {
  list: (project_id?: string) =>
    get<any[]>(`/repos/${project_id ? `?project_id=${project_id}` : ''}`),
  create: (project_id: string, name: string, url: string, branch: string) =>
    post<any>('/repos/', { project_id, name, url, branch }),
  switchBranch: (id: string, branch: string) =>
    post<any>(`/repos/${id}/switch-branch`, { branch }),
  sync: (id: string) => post<any>(`/repos/${id}/sync`),
};

// ── Agents ────────────────────────────────────────────────────────────────────
export const agentsApi = {
  list: (project_id?: string) =>
    get<any[]>(`/agents/${project_id ? `?project_id=${project_id}` : ''}`),
  create: (project_id: string, name: string, prompt: string, skills: string[]) =>
    post<any>('/agents/', { project_id, name, prompt, skills }),
  get: (id: string) => get<any>(`/agents/${id}`),
  update: (id: string, data: Record<string, unknown>) => put<any>(`/agents/${id}`, data),
  delete: (id: string) => del(`/agents/${id}`),
};

// ── Tasks ─────────────────────────────────────────────────────────────────────
export const tasksApi = {
  list: (project_id?: string) =>
    get<any[]>(`/tasks/${project_id ? `?project_id=${project_id}` : ''}`),
  create: (project_id: string, title: string, description: string, assignee_id?: string) =>
    post<any>('/tasks/', { project_id, title, description, assignee_id }),
  get: (id: string) => get<any>(`/tasks/${id}`),
  update: (id: string, data: Record<string, unknown>) => put<any>(`/tasks/${id}`, data),
  listComments: (id: string) => get<any[]>(`/tasks/${id}/comments`),
  addComment: (id: string, content: string) =>
    post<any>(`/tasks/${id}/comments`, { content }),
  listHistory: (id: string) => get<any[]>(`/tasks/${id}/history`),
};

// ── Knowledge ─────────────────────────────────────────────────────────────────
export const knowledgeApi = {
  list: (q?: string) => get<any[]>(`/knowledge/${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  create: (project_id: string, title: string, content: string, tags: string[]) =>
    post<any>('/knowledge/', { project_id, title, content, tags }),
  get: (id: string) => get<any>(`/knowledge/${id}`),
  update: (id: string, data: Record<string, unknown>) => put<any>(`/knowledge/${id}`, data),
  delete: (id: string) => del(`/knowledge/${id}`),
};

// ── Plugins ───────────────────────────────────────────────────────────────────
export const pluginsApi = {
  list: () => get<any[]>('/plugins/'),
  install: (team_id: string, name: string, description: string, version: string, config: Record<string, unknown>) =>
    post<any>('/plugins/', { team_id, name, description, version, config }),
  update: (id: string, data: Record<string, unknown>) => put<any>(`/plugins/${id}`, data),
  uninstall: (id: string) => del(`/plugins/${id}`),
  obsLogs: () => get<any[]>('/plugins/observability/logs'),
};

// ── Feedbacks ─────────────────────────────────────────────────────────────────
export const feedbacksApi = {
  list: (resource_type?: string, resource_id?: string) => {
    const params = new URLSearchParams();
    if (resource_type) params.set('resource_type', resource_type);
    if (resource_id) params.set('resource_id', resource_id);
    const qs = params.toString();
    return get<any[]>(`/feedbacks/${qs ? `?${qs}` : ''}`);
  },
  create: (resource_type: string, resource_id: string, content: string, rating?: number) =>
    post<any>('/feedbacks/', { resource_type, resource_id, content, rating }),
  auditLogs: (resource_type?: string) =>
    get<any[]>(`/auditlogs/${resource_type ? `?resource_type=${resource_type}` : ''}`),
};

// ── Settings ──────────────────────────────────────────────────────────────────
export const settingsApi = {
  getMe: () => get<any>('/settings/me'),
  updateMe: (data: Record<string, unknown>) => put<any>('/settings/me', data),
  locales: () => get<any[]>('/settings/locales'),
  translations: (locale: string) => get<any>(`/settings/translations/${locale}`),
};

// ═══════════════════════════════════════════════════════════════════════════════
// AI 治理层  — base path is /api (not /api/v1)
// ═══════════════════════════════════════════════════════════════════════════════
const GOV_BASE = '/api';

async function govReq<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${GOV_BASE}${path}`, { ...options, headers });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    handleAuthExpiry(resp.status, String(err.detail ?? resp.statusText));
    throw new Error(err.detail ?? resp.statusText);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json();
}

async function govReqBlob(path: string, options: RequestInit = {}): Promise<Blob> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${GOV_BASE}${path}`, { ...options, headers });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    handleAuthExpiry(resp.status, String(err.detail ?? resp.statusText));
    throw new Error(err.detail ?? resp.statusText);
  }
  return resp.blob();
}

const govGet  = <T>(path: string) => govReq<T>(path);
const govPost = <T>(path: string, body?: unknown) =>
  govReq<T>(path, { method: 'POST', body: JSON.stringify(body) });
const govPatch = <T>(path: string, body?: unknown) =>
  govReq<T>(path, { method: 'PATCH', body: JSON.stringify(body) });
const govDel  = <T>(path: string) => govReq<T>(path, { method: 'DELETE' });

// ── Virtual Keys ──────────────────────────────────────────────────────────────
export const keysApi = {
  list: (params?: { status?: string; q?: string }) => {
    const qs = new URLSearchParams(
      Object.entries(params ?? {}).filter(([, v]) => v != null) as [string, string][]
    ).toString();
    return govGet<{ items: any[]; total: number }>(`/keys${qs ? `?${qs}` : ''}`);
  },
  issue: (data: { label?: string; user_id?: string; scope?: string; expires_days?: number; quota?: number }) =>
    govPost<{ key_id: string; key_secret: string; label?: string; status: string }>(
      '/keys/issue',
      { user_id: 'admin', scope: 'project:*', ...data },
    ),
  revoke:   (id: string) => govDel<void>(`/keys/${id}`),
  auditLog: (id: string) => govGet<any>(`/keys/${id}/audit-log`),
  usage:    (id: string) => govGet<any>(`/keys/${id}/usage`),
};

// ── Model Registry ────────────────────────────────────────────────────────────
export const modelsApi = {
  list: (provider?: string, provider_id?: string, limit?: number, offset?: number) => {
    const qs = new URLSearchParams(
      Object.entries({ provider, provider_id, limit, offset })
        .filter(([, v]) => v != null && v !== '') as [string, string][]
    ).toString();
    return govGet<{ items: any[]; total: number }>(`/models${qs ? `?${qs}` : ''}`);
  },
  register: (data: any) => govPost<any>('/models', data),
  batchRegister: (models: any[]) => govPost<{ total: number; registered: number; skipped: number; items: any[] }>(
    '/models/batch-register',
    { models },
  ),
  update:   (id: string, data: any) => govPatch<any>(`/models/${id}`, data),
  delete:   (id: string) => govDel<void>(`/models/${id}`),
  batchDelete: (model_ids: string[]) => govPost<{ total: number; deleted: number; deleted_ids: string[]; missing_ids: string[] }>(
    '/models/batch-delete',
    { model_ids },
  ),
  aliases:  () => govGet<any>('/models/aliases'),
};

// ── AI Providers ──────────────────────────────────────────────────────────────
export const providersApi = {
  list:    () => govGet<{ items: any[]; total: number }>('/providers'),
  presets: () => govGet<any[]>('/providers/presets'),
  get:     (id: string) => govGet<any>(`/providers/${id}`),
  create:  (data: any) => govPost<any>('/providers', data),
  update:  (id: string, data: any) => govPatch<any>(`/providers/${id}`, data),
  delete:  (id: string) => govDel<void>(`/providers/${id}`),
  sync:    (id: string, data?: { target_apps?: string[]; sync_models?: boolean }) =>
    govPost<any>(`/providers/${id}/sync`, data ?? { sync_models: true }),
  discoverModels: (id: string) => govPost<{ provider_id: string; endpoint: string; models: string[]; fetched_at: string }>(`/providers/${id}/discover-models`),
  syncGateway: () => govPost<any>('/providers/sync-gateway'),
};

// ── Skills ────────────────────────────────────────────────────────────────────
export const skillsApi = {
  list:   () => govGet<{ items: any[]; total: number }>('/skills'),
  search: (query: string) =>
    govGet<{ items: any[]; total: number }>(`/skills/search?query=${encodeURIComponent(query)}`),
  get: (id: string) => govGet<any>(`/skills/${id}`),
  exportPack: (id: string, target: 'claude-code' | 'opencode') =>
    govGet<any>(`/skills/${id}/pack/${target}`),
  exportPackZip: (id: string, target: 'claude-code' | 'opencode') =>
    govReqBlob(`/skills/${id}/pack-zip/${target}.zip`),
  update: (id: string, data: { name?: string; description?: string; system_prompt?: string; category?: string; tags?: string[]; status?: string }) =>
    govPatch<any>(`/skills/${id}`, data),
  create: (data: { name: string; description?: string; category?: string; system_prompt?: string; tags?: string[] }) =>
    govPost<any>('/skills', data),
  delete: (id: string) => govDel<void>(`/skills/${id}`),
};

// ── AI Sessions ───────────────────────────────────────────────────────────────
export const sessionsApi = {
  list:   () => govGet<{ items: any[]; total: number }>('/sessions'),
  create: (data: { user_id: string; project_id?: string; title?: string }) =>
    govPost<any>('/sessions', data),
  update: (id: string, data: { title?: string; status?: string }) =>
    govPatch<any>(`/sessions/${id}`, data),
};

// ── Policies ──────────────────────────────────────────────────────────────────
export const policiesApi = {
  list:   () => govGet<{ items: any[]; total: number }>('/policies'),
  upsert: (data: { name: string; type: string; rules?: Record<string, unknown>; status?: string }) =>
    govPost<any>('/policies', data),
};

// ── Approvals ─────────────────────────────────────────────────────────────────
export const approvalsApi = {
  list:   () => govGet<{ items: any[]; total: number }>('/approvals'),
  submit: (data: { applicant_id: string; action: string; resource_id: string; reason: string }) =>
    govPost<any>('/approvals/submit', data),
  get:    (id: string) => govGet<any>(`/approvals/${id}`),
};

// ── Platform Overview ─────────────────────────────────────────────────────────
export const platformApi = {
  overview: () => govGet<any>('/platform/overview'),
  runtimeHealth: () => govGet<any>('/platform/runtime-health'),
};

// ── Runtime Config ────────────────────────────────────────────────────────────
export const runtimeApi = {
  previewLitellm: () => govGet<any>('/v1/runtime/litellm-config'),
  applyLitellm:   (output_dir = '') =>
    govPost<any>('/v1/runtime/litellm-config/apply', { output_dir }),
  clientConfig: (app: string, opts?: { apiKey?: string; baseUrl?: string }) => {
    const params = new URLSearchParams();
    if (opts?.apiKey) params.set('api_key', opts.apiKey);
    if (opts?.baseUrl) params.set('base_url', opts.baseUrl);
    const qs = params.toString();
    return govGet<any>(`/v1/runtime/client-config/${app}${qs ? '?' + qs : ''}`);
  },
};

// ── Learning Loop / Skill GitOps ─────────────────────────────────────────────
export const learningApi = {
  taskRuns: (limit = 20, offset = 0) =>
    govGet<{ items: any[]; total: number }>(`/task-runs?limit=${limit}&offset=${offset}`),
  skillUpdates: (opts?: { status?: string; skill_id?: string; limit?: number; offset?: number }) => {
    const params = new URLSearchParams();
    if (opts?.status) params.set('status', opts.status);
    if (opts?.skill_id) params.set('skill_id', opts.skill_id);
    params.set('limit', String(opts?.limit ?? 20));
    params.set('offset', String(opts?.offset ?? 0));
    return govGet<{ items: any[]; total: number }>(`/skill-updates?${params.toString()}`);
  },
  applySkillUpdate: (updateId: string) =>
    govPost<any>(`/skill-updates/${updateId}/apply`, {}),
  gitRepos: (limit = 50, offset = 0) =>
    govGet<{ items: any[]; total: number }>(`/git-repos?limit=${limit}&offset=${offset}`),
  pullRepo: (repoId: string) =>
    govPost<any>(`/git-repos/${repoId}/pull`, {}),
  hookEvents: (limit = 50, offset = 0) =>
    govGet<{ items: any[]; total: number }>(`/skill-sync/hooks/events?limit=${limit}&offset=${offset}`),
  hookSecretStatus: () =>
    govGet<any>('/skill-sync/hooks/secret'),
  rotateHookSecret: (newSecret?: string) =>
    govPost<any>('/skill-sync/hooks/secret/rotate', { new_secret: newSecret || null }),
  uploadSkillBundle: (data: {
    team_id: string;
    skill_id: string;
    version?: string;
    bundle?: Record<string, unknown>;
    tags?: string[];
    uploaded_by?: string;
  }) =>
    govPost<any>('/skill-sync/mcp/skill-bundles/upload', {
      version: 'v1',
      bundle: {},
      tags: [],
      ...data,
    }),
  downloadSkillBundle: (skillId: string, version?: string) =>
    govGet<any>(
      `/skill-sync/mcp/skill-bundles/download?skill_id=${encodeURIComponent(skillId)}${
        version ? `&version=${encodeURIComponent(version)}` : ''
      }`,
    ),
  generateTeamRules: (teamId: string) =>
    govPost<any>(
      `/skill-sync/mcp/team-rules/generate?team_id=${encodeURIComponent(teamId)}`,
      {},
    ),
  applyTeamRules: (teamId: string, ruleSetId: string, dryRun = false) =>
    govPost<any>(
      `/skill-sync/mcp/team-rules/${encodeURIComponent(ruleSetId)}/apply?team_id=${encodeURIComponent(teamId)}`,
      { dry_run: dryRun },
    ),
  ingestGatewayKnowledge: (data: {
    items: Array<{
      source_type: 'session' | 'cli';
      source_id: string;
      content: string;
      title?: string;
      module?: string;
      team_id?: string;
      tags?: string[];
      quality_score?: number;
      metadata?: Record<string, unknown>;
    }>;
    min_quality_score?: number;
    created_by?: string;
  }) =>
    govPost<any>('/evolution/gateway-knowledge/ingest', data),
  summarizeRagToSkill: (data?: { scope?: string; limit?: number; created_by?: string }) =>
    govPost<any>('/evolution/rag-to-skill/summarize', {
      scope: 'team',
      limit: 20,
      ...data,
    }),
  generateAgentWorkflow: (data?: { scope?: string; constraints?: Record<string, unknown>; created_by?: string }) =>
    govPost<any>('/evolution/rag-to-agent/generate', {
      scope: 'team',
      constraints: {},
      ...data,
    }),
  optimizeAgentWorkflow: (workflowId: string, feedbackWindow = 20) =>
    govPost<any>(
      `/evolution/rag-to-agent/${encodeURIComponent(workflowId)}/optimize`,
      { feedback_window: feedbackWindow },
    ),
  listAgentWorkflows: (limit = 20, offset = 0) =>
    govGet<{ items: any[]; total: number }>(
      `/evolution/rag-to-agent/workflows?limit=${limit}&offset=${offset}`,
    ),
  evolutionOverview: () => govGet<any>('/evolution/overview'),
  evolutionActions: (limit = 50, offset = 0) =>
    govGet<{ items: any[]; total: number }>(
      `/evolution/actions?limit=${limit}&offset=${offset}`,
    ),
};
