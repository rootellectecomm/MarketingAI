import { campaigns, comments, leads, metrics } from "@/lib/mock-data";
import type {
  BootstrapResponse,
  Campaign,
  CampaignCreate,
  CommentItem,
  ContentGenerateResult,
  ConversationItem,
  ConversationMessage,
  DashboardMetrics,
  FunnelSummary,
  KnowledgeDocument,
  KnowledgeCreate,
  Lead,
  MetaConnectUrl,
  MetaSyncResult,
  ProviderStatus,
  TokenResponse
} from "@/types/api";

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
  backend_reachable: false,
  provider_mode: PROVIDER_MODE,
  facebook_ready: false,
  instagram_ready: false,
  whatsapp_ready: false,
  openai_ready: false,
  chroma_collection: "rootellect_knowledge",
  meta_env_ready: false,
  setup_warnings: [
    "Cannot read backend provider status. Check NEXT_PUBLIC_API_BASE_URL on the frontend Vercel project and redeploy."
  ],
  facebook_pages: [],
  instagram_accounts: []
};

function handleUnauthorized(response: Response) {
  if (response.status !== 401 || typeof window === "undefined") {
    return;
  }
  localStorage.removeItem("rootellect_token");
  document.cookie = "rootellect_token=; path=/; max-age=0";
  if (window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}

async function getJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const token = typeof window !== "undefined" ? localStorage.getItem("rootellect_token") : null;
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      cache: "no-store"
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
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store"
  });
  if (!response.ok) {
    handleUnauthorized(response);
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as T;
}

async function readApiError(response: Response): Promise<string> {
  const raw = await response.text();
  if (!raw) {
    return response.status === 500
      ? "Internal Server Error. Check backend logs and DATABASE_URL."
      : `Request failed with ${response.status}`;
  }
  if (raw.startsWith("<")) {
    return response.status === 500
      ? "Internal Server Error. Backend may be unreachable."
      : `Request failed with ${response.status}`;
  }
  try {
    const data = JSON.parse(raw) as {
      detail?: string | Array<{ msg?: string }> | { meta_error?: { error?: { message?: string; code?: number } }; fix?: string };
      error?: string;
      fix?: string;
    };
    if (typeof data.detail === "string") {
      return data.detail;
    }
    if (data.detail && !Array.isArray(data.detail) && typeof data.detail === "object") {
      const metaMessage = data.detail.meta_error?.error?.message;
      const metaCode = data.detail.meta_error?.error?.code;
      if (metaMessage) {
        return metaCode ? `Meta API error ${metaCode}: ${metaMessage}` : `Meta API error: ${metaMessage}`;
      }
      if (typeof data.detail.fix === "string") {
        return data.detail.fix;
      }
    }
    if (typeof data.error === "string") {
      return data.fix ? `${data.error} ${data.fix}` : data.error;
    }
    if (Array.isArray(data.detail)) {
      return data.detail.map((item) => item.msg ?? JSON.stringify(item)).join("; ");
    }
    return raw;
  } catch {
    return raw;
  }
}

async function authProxyPost<T>(path: string, body?: unknown, options?: { allowStatuses?: number[] }): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store"
    });
  } catch {
    throw new Error(
      "Cannot reach the login proxy. Ensure `npm run dev` is running and BACKEND_API_BASE_URL in frontend/.env.local points to a live API."
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
  const response = await fetch("/api/auth/reset-admin", { method: "POST", cache: "no-store" });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
}

export const api = {
  resetAdmin,
  bootstrap: () => authProxyPost<BootstrapResponse>("/api/auth/bootstrap", undefined, { allowStatuses: [409] }),
  login: (email: string, password: string) => authProxyPost<TokenResponse>("/api/auth/login", { email, password }),
  metrics: () => getJson<DashboardMetrics>("/dashboard/metrics", USE_MOCK_DATA ? metrics : emptyMetrics),
  comments: () => getJson<CommentItem[]>("/comments", USE_MOCK_DATA ? comments : []),
  leads: () => getJson<Lead[]>("/leads", USE_MOCK_DATA ? leads : []),
  campaigns: () => getJson<Campaign[]>("/campaigns", USE_MOCK_DATA ? campaigns : []),
  createCampaign: (payload: CampaignCreate) => postJson<Campaign>("/campaigns", payload),
  conversations: () => getJson<ConversationItem[]>("/conversations", []),
  conversationMessages: (id: string) => getJson<ConversationMessage[]>(`/conversations/${id}/messages`, []),
  knowledge: () => getJson<KnowledgeDocument[]>("/knowledge", []),
  createKnowledge: (payload: KnowledgeCreate) => postJson<KnowledgeDocument>("/knowledge", payload),
  funnels: () => getJson<FunnelSummary[]>("/funnels", []),
  generateContent: (payload: { content_type: string; topic: string; product_focus?: string[] }) =>
    postJson<ContentGenerateResult>("/content/generate", payload),
  aiLogs: () => getJson<Array<Record<string, unknown>>>("/ai-logs", []),
  moderation: () => getJson<Array<Record<string, unknown>>>("/moderation", []),
  webhooks: () => getJson<Array<Record<string, unknown>>>("/webhooks/logs", []),
  metaConnectUrl: () => getJson<MetaConnectUrl>("/meta/connect-url", { status: "setup_required" }),
  syncMetaComments: (params = { media_limit: 8, comments_per_media: 25 }) =>
    postJson<MetaSyncResult>(
      `/meta/sync/comments?media_limit=${params.media_limit}&comments_per_media=${params.comments_per_media}`
    ),
  providerStatus: () =>
    getJson<ProviderStatus>(
      "/settings/providers",
      USE_MOCK_DATA
        ? {
            backend_reachable: true,
            provider_mode: PROVIDER_MODE,
            facebook_ready: PROVIDER_MODE !== "mock",
            instagram_ready: PROVIDER_MODE !== "mock",
            whatsapp_ready: process.env.NEXT_PUBLIC_WHATSAPP_READY === "true",
            openai_ready: process.env.NEXT_PUBLIC_OPENAI_READY !== "false",
            chroma_collection: "rootellect_knowledge",
            meta_env_ready: PROVIDER_MODE !== "mock",
            setup_warnings: [],
            facebook_pages: [],
            instagram_accounts: []
          }
        : liveProviderFallback
    )
};
