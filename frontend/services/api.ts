import { campaigns, comments, leads, metrics } from "@/lib/mock-data";
import type { Campaign, CommentItem, DashboardMetrics, Lead, MetaSyncResult, ProviderStatus, TokenResponse } from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const PROVIDER_MODE = process.env.NEXT_PUBLIC_PROVIDER_MODE ?? "facebook_page_backed";
const USE_MOCK_DATA = process.env.NEXT_PUBLIC_USE_MOCK_DATA === "true";

const emptyMetrics: DashboardMetrics = {
  comments: 0,
  leads: 0,
  automated_actions: 0,
  escalations: 0,
  avg_ai_confidence: 0,
  sentiment: {},
  latest_activity: []
};

const liveProviderFallback: ProviderStatus = {
  provider_mode: PROVIDER_MODE,
  facebook_ready: false,
  instagram_ready: false,
  whatsapp_ready: false,
  openai_ready: false,
  chroma_collection: "rootellect_knowledge"
};

function handleUnauthorized(response: Response) {
  if (response.status !== 401 || typeof window === "undefined") {
    return;
  }
  localStorage.removeItem("rootellect_token");
  if (window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}

async function getJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const token = typeof window !== "undefined" ? localStorage.getItem("rootellect_token") : null;
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      next: { revalidate: 15 }
    });
    if (!response.ok) {
      handleUnauthorized(response);
      return fallback;
    }
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("rootellect_token") : null;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  if (!response.ok) {
    handleUnauthorized(response);
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }
  return (await response.json()) as T;
}

async function readApiError(response: Response): Promise<string> {
  const raw = await response.text();
  if (!raw) {
    return `Request failed with ${response.status}`;
  }
  try {
    const data = JSON.parse(raw) as { detail?: string | Array<{ msg?: string }> };
    if (typeof data.detail === "string") {
      return data.detail;
    }
    if (Array.isArray(data.detail)) {
      return data.detail.map((item) => item.msg ?? JSON.stringify(item)).join("; ");
    }
    return raw;
  } catch {
    return raw;
  }
}

async function authPost<T>(path: string, body?: unknown, options?: { allowStatuses?: number[] }): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body)
    });
  } catch {
    throw new Error(
      `Cannot reach backend at ${API_BASE_URL}. Set NEXT_PUBLIC_API_BASE_URL on the frontend Vercel project to https://marketing-ai-gymu.vercel.app/api/v1 and redeploy the backend.`
    );
  }
  if (!response.ok && !options?.allowStatuses?.includes(response.status)) {
    throw new Error(await readApiError(response));
  }
  if (!response.ok) {
    return {} as T;
  }
  return (await response.json()) as T;
}

async function resetAdmin(): Promise<void> {
  let response: Response;
  try {
    response = await fetch("/api/auth/reset-admin", { method: "POST", cache: "no-store" });
  } catch {
    throw new Error("Cannot reach the reset-admin proxy on this frontend deployment.");
  }
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { error?: string } | null;
    throw new Error(payload?.error ?? `Admin reset failed with status ${response.status}`);
  }
}

export const api = {
  resetAdmin,
  bootstrap: () => authPost("/auth/bootstrap", undefined, { allowStatuses: [409] }),
  login: (email: string, password: string) => authPost<TokenResponse>("/auth/login", { email, password }),
  metrics: () => getJson<DashboardMetrics>("/dashboard/metrics", USE_MOCK_DATA ? metrics : emptyMetrics),
  comments: () => getJson<CommentItem[]>("/comments", USE_MOCK_DATA ? comments : []),
  leads: () => getJson<Lead[]>("/leads", USE_MOCK_DATA ? leads : []),
  campaigns: () => getJson<Campaign[]>("/campaigns", USE_MOCK_DATA ? campaigns : []),
  aiLogs: () => getJson<Array<Record<string, unknown>>>("/ai-logs", []),
  moderation: () => getJson<Array<Record<string, unknown>>>("/moderation", []),
  webhooks: () => getJson<Array<Record<string, unknown>>>("/webhooks/logs", []),
  syncMetaComments: (params = { media_limit: 8, comments_per_media: 25 }) =>
    postJson<MetaSyncResult>(
      `/meta/sync/comments?media_limit=${params.media_limit}&comments_per_media=${params.comments_per_media}`
    ),
  providerStatus: () =>
    getJson<ProviderStatus>(
      "/settings/providers",
      USE_MOCK_DATA
        ? {
            provider_mode: PROVIDER_MODE,
            facebook_ready: PROVIDER_MODE !== "mock",
            instagram_ready: PROVIDER_MODE !== "mock",
            whatsapp_ready: process.env.NEXT_PUBLIC_WHATSAPP_READY === "true",
            openai_ready: process.env.NEXT_PUBLIC_OPENAI_READY !== "false",
            chroma_collection: "rootellect_knowledge"
          }
        : liveProviderFallback
    )
};
