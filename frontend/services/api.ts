import { campaigns, comments, leads, metrics } from "@/lib/mock-data";
import type { Campaign, CommentItem, DashboardMetrics, Lead } from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function getJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const token = typeof window !== "undefined" ? localStorage.getItem("rootellect_token") : null;
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      next: { revalidate: 15 }
    });
    if (!response.ok) {
      return fallback;
    }
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

export const api = {
  metrics: () => getJson<DashboardMetrics>("/dashboard/metrics", metrics),
  comments: () => getJson<CommentItem[]>("/comments", comments),
  leads: () => getJson<Lead[]>("/leads", leads),
  campaigns: () => getJson<Campaign[]>("/campaigns", campaigns),
  aiLogs: () => getJson<Array<Record<string, unknown>>>("/ai-logs", []),
  moderation: () => getJson<Array<Record<string, unknown>>>("/moderation", []),
  webhooks: () => getJson<Array<Record<string, unknown>>>("/webhooks/logs", []),
  providerStatus: () =>
    getJson("/settings/providers", {
      provider_mode: "mock",
      instagram_ready: false,
      whatsapp_ready: false,
      openai_ready: false,
      chroma_collection: "rootellect_knowledge"
    })
};
