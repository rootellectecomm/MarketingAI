import type { Campaign, CommentItem, DashboardMetrics, Lead } from "@/types/api";

export const metrics: DashboardMetrics = {
  comments: 1284,
  leads: 312,
  automated_actions: 941,
  escalations: 27,
  avg_ai_confidence: 0.86,
  sentiment: { positive: 540, neutral: 612, negative: 132 },
  latest_activity: [
    { id: "a1", confidence: 0.91, blocked: false, created_at: "2026-05-14T09:12:00Z" },
    { id: "a2", confidence: 0.64, blocked: true, created_at: "2026-05-14T08:48:00Z" },
    { id: "a3", confidence: 0.88, blocked: false, created_at: "2026-05-14T08:20:00Z" }
  ]
};

export const comments: CommentItem[] = [
  {
    id: "c1",
    provider_comment_id: "ig_9831",
    media_id: "reel_41",
    username: "wellnesswithriya",
    text: "Is Mind Calm good for daily stress?",
    normalized_text: "Is Mind Calm good for daily stress?",
    hidden: false,
    replied: true,
    private_replied: true,
    created_at: "2026-05-14T08:12:00Z"
  },
  {
    id: "c2",
    provider_comment_id: "ig_9832",
    media_id: "reel_37",
    username: "fitmomsclub",
    text: "Need price for PCOS Support",
    normalized_text: "Need price for PCOS Support",
    hidden: false,
    replied: true,
    private_replied: true,
    created_at: "2026-05-14T07:58:00Z"
  },
  {
    id: "c3",
    provider_comment_id: "ig_9833",
    media_id: "reel_22",
    username: "unknown",
    text: "Can this cure menopause symptoms?",
    normalized_text: "Can this cure menopause symptoms?",
    hidden: false,
    replied: false,
    private_replied: false,
    created_at: "2026-05-14T07:37:00Z"
  }
];

export const leads: Lead[] = [
  {
    id: "l1",
    external_user_id: "1781",
    username: "wellnesswithriya",
    source_channel: "instagram",
    lifecycle_stage: "hot",
    phone: null,
    whatsapp_opt_in: false,
    score: 91,
    tags: ["instagram", "Mind Calm"],
    created_at: "2026-05-13T12:00:00Z"
  },
  {
    id: "l2",
    external_user_id: "1782",
    username: "fitmomsclub",
    source_channel: "instagram",
    lifecycle_stage: "qualified",
    phone: "+91********12",
    whatsapp_opt_in: true,
    score: 78,
    tags: ["instagram", "PCOS Support"],
    created_at: "2026-05-12T12:00:00Z"
  }
];

export const campaigns: Campaign[] = [
  {
    id: "campaign-1",
    name: "Mind Calm reel launch",
    status: "active",
    product_focus: ["Mind Calm"],
    keyword_triggers: ["stress", "sleep", "calm"],
    public_reply_enabled: true,
    dm_enabled: true,
    whatsapp_followup_enabled: false,
    created_at: "2026-05-10T12:00:00Z"
  },
  {
    id: "campaign-2",
    name: "PCOS education comments",
    status: "active",
    product_focus: ["PCOS Support"],
    keyword_triggers: ["pcos", "cycle", "hormone"],
    public_reply_enabled: true,
    dm_enabled: true,
    whatsapp_followup_enabled: true,
    created_at: "2026-05-09T12:00:00Z"
  }
];

