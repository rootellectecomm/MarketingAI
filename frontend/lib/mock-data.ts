import type { Campaign, CommentItem, DashboardMetrics, Giveaway, GiveawayAnalytics, GiveawayParticipant, Lead } from "@/types/api";

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
    platform: "instagram",
    lifecycle_stage: "hot",
    phone: null,
    product_interest: "Mind Calm",
    intent_level: "high",
    last_message: "Need link for Mind Calm",
    source_campaign_id: "campaign-1",
    conversion_stage: "hot_lead",
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
    platform: "instagram",
    lifecycle_stage: "qualified",
    phone: "+91********12",
    product_interest: "PCOS Support",
    intent_level: "medium",
    last_message: "Need price for PCOS Support",
    source_campaign_id: "campaign-2",
    conversion_stage: "dm_sent",
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
    platform: "both",
    post_id: null,
    product_key: "mind_calm",
    product_name: "Mind Calm",
    product_link: "https://www.rootellect.com/products/mind-calm",
    followup_link: "https://www.rootellect.com/products/mind-calm",
    whatsapp_link: "https://wa.me/918679508311",
    product_focus: ["Mind Calm"],
    keyword_triggers: ["stress", "sleep", "calm"],
    public_reply_template: "Sent you the details in DM.",
    dm_template:
      "Got it. Mind Calm is the closest fit if your concern is stress, overthinking or sleep quality. {{product_link}}",
    ai_prompt_override: null,
    public_reply_enabled: true,
    dm_enabled: true,
    whatsapp_followup_enabled: false,
    ai_followup_enabled: true,
    metadata_json: { target_media_urls: [], target_media_ids: [], target_media_shortcodes: [] },
    created_at: "2026-05-10T12:00:00Z"
  },
  {
    id: "campaign-2",
    name: "PCOS education comments",
    status: "active",
    platform: "both",
    post_id: null,
    product_key: "pcos_support",
    product_name: "PCOS Support",
    product_link: "https://www.rootellect.com/products/pcos-pcod-support",
    followup_link: "https://www.rootellect.com/products/pcos-pcod-support",
    whatsapp_link: "https://wa.me/918679508311",
    product_focus: ["PCOS Support"],
    keyword_triggers: ["pcos", "cycle", "hormone"],
    public_reply_template: "Sent you the details in DM.",
    dm_template:
      "For PCOS/PCOD wellness, PCOS Support is the most relevant option. {{product_link}}",
    ai_prompt_override: null,
    public_reply_enabled: true,
    dm_enabled: true,
    whatsapp_followup_enabled: true,
    ai_followup_enabled: true,
    metadata_json: { target_media_urls: [], target_media_ids: [], target_media_shortcodes: [] },
    created_at: "2026-05-09T12:00:00Z"
  }
];

export const giveaways: Giveaway[] = [
  {
    id: "giveaway-1",
    name: "Mind Calm giveaway",
    status: "active",
    media_id: "reel_41",
    media_permalink: "https://www.instagram.com/reel/mindcalm/",
    trigger_type: "keyword_match",
    trigger_keywords: ["calm", "sleep", "stress", "overthinking"],
    public_reply_text: "Thanks for joining. Please check your DM.",
    public_reply_variations: ["You're in. Check your DM.", "Thanks for joining - details sent in DM."],
    dm_message_text: "You're in. Follow Rootellect and reply I have followed to receive your Mind Calm wellness guide.",
    follow_button_text: "I have followed",
    reply_limit: 500,
    cooldown_hours: 24,
    exclusion_keywords: ["fake", "scam", "bad", "not interested"],
    brand_signature: "Rootellect",
    starts_at: null,
    ends_at: null,
    metadata_json: {},
    created_at: "2026-05-20T09:00:00Z",
    participant_count: 128,
    reward_sent_count: 76,
    content: {
      content_type: "coupon",
      coupon_code: "MINDCALM10",
      message_text: "Here is your Mind Calm sleep routine and giveaway coupon.",
      cta_label: "Open guide",
      cta_url: "https://rootellect.com"
    }
  }
];

export const giveawayParticipants: GiveawayParticipant[] = [
  {
    id: "participant-1",
    automation_id: "giveaway-1",
    instagram_user_id: "1781",
    instagram_username: "wellnesswithriya",
    comment_text: "Need calm sleep guide",
    trigger_matched: "calm",
    status: "reward_sent",
    reward_sent: true,
    error_message: null,
    tags: ["giveaway", "winner"],
    created_at: "2026-05-20T09:15:00Z"
  },
  {
    id: "participant-2",
    automation_id: "giveaway-1",
    instagram_user_id: "1782",
    instagram_username: "fitmomsclub",
    comment_text: "stress routine pls",
    trigger_matched: "stress",
    status: "dm_sent",
    reward_sent: false,
    error_message: null,
    tags: ["giveaway"],
    created_at: "2026-05-20T09:18:00Z"
  }
];

export const giveawayAnalytics: GiveawayAnalytics = {
  total_comments_captured: 164,
  valid_participants: 128,
  excluded_comments: 9,
  dms_sent: 118,
  rewards_claimed: 76,
  conversion_rate: 59.38,
  top_trigger_keywords: [
    { keyword: "calm", count: 46 },
    { keyword: "sleep", count: 39 },
    { keyword: "stress", count: 31 }
  ],
  post_performance: [{ automation_id: "giveaway-1", participants: 128 }]
};
