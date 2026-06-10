export type DashboardMetrics = {
  comments: number;
  leads: number;
  automated_actions: number;
  escalations: number;
  avg_ai_confidence: number;
  sentiment: Record<string, number>;
  latest_activity: Array<Record<string, string | number | boolean>>;
};

export type CommentItem = {
  id: string;
  provider_comment_id: string;
  media_id: string | null;
  username: string | null;
  text: string;
  normalized_text: string;
  hidden: boolean;
  replied: boolean;
  private_replied: boolean;
  created_at: string;
};

export type Lead = {
  id: string;
  external_user_id: string;
  username: string | null;
  source_channel: string;
  platform: string;
  lifecycle_stage: string;
  phone: string | null;
  product_interest: string | null;
  intent_level: string;
  last_message: string | null;
  source_campaign_id: string | null;
  conversion_stage: string;
  whatsapp_opt_in: boolean;
  score: number;
  tags: string[];
  created_at: string;
};

export type Campaign = {
  id: string;
  name: string;
  status: string;
  platform: string;
  post_id: string | null;
  product_key: string | null;
  product_name: string | null;
  product_link: string | null;
  followup_link: string | null;
  whatsapp_link: string | null;
  product_focus: string[];
  keyword_triggers: string[];
  public_reply_template: string;
  dm_template: string;
  ai_prompt_override: string | null;
  public_reply_enabled: boolean;
  dm_enabled: boolean;
  whatsapp_followup_enabled: boolean;
  ai_followup_enabled: boolean;
  metadata_json: {
    target_media_urls?: string[];
    target_media_ids?: string[];
    target_media_shortcodes?: string[];
    [key: string]: unknown;
  };
  created_at: string;
};

export type User = {
  id: string;
  email: string;
  full_name: string;
  role: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type BootstrapResponse = {
  created: boolean;
  user: User;
};

export type ProviderStatus = {
  backend_reachable?: boolean;
  provider_mode: string;
  facebook_ready: boolean;
  instagram_ready: boolean;
  whatsapp_ready: boolean;
  openai_ready: boolean;
  chroma_collection: string;
  meta_env_ready?: boolean;
  missing_meta_env?: string[];
  setup_warnings?: string[];
  facebook_pages?: Array<{
    id: string | null;
    name: string;
    updated_at: string | null;
  }>;
  instagram_accounts?: Array<{
    id: string;
    username: string;
    auth_path: string;
    updated_at: string | null;
  }>;
};

export type ConversationItem = {
  id: string;
  external_user_id: string;
  username: string | null;
  channel: string;
  last_message_at: string | null;
  is_open: boolean;
};

export type ConversationMessage = {
  id: string;
  direction: string;
  body: string;
  channel: string;
  created_at: string;
};

export type KnowledgeDocument = {
  id: string;
  title: string;
  category: string;
  content: string;
  source: string;
  is_active: boolean;
  created_at: string;
};

export type KnowledgeCreate = {
  title: string;
  category: string;
  content: string;
  source?: string;
};

export type CampaignCreate = {
  name: string;
  status?: string;
  platform?: string;
  post_id?: string | null;
  product_key?: string | null;
  product_name?: string | null;
  product_link?: string | null;
  followup_link?: string | null;
  whatsapp_link?: string | null;
  product_focus?: string[];
  keyword_triggers?: string[];
  public_reply_template?: string;
  dm_template?: string;
  ai_prompt_override?: string | null;
  public_reply_enabled?: boolean;
  dm_enabled?: boolean;
  whatsapp_followup_enabled?: boolean;
  ai_followup_enabled?: boolean;
  metadata_json?: Campaign["metadata_json"];
};

export type CampaignEvent = {
  id: string;
  campaign_id: string;
  platform: string;
  source_type: string;
  user_id: string | null;
  username: string | null;
  comment_id: string | null;
  message_id: string | null;
  matched_keyword: string | null;
  user_text: string;
  ai_intent: string | null;
  lead_score: number;
  status: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
};

export type CampaignTestResult = {
  matched_campaign: Campaign | null;
  matched_keyword: string | null;
  public_reply_preview: string;
  dm_preview: string;
  product_selected: string | null;
  lead_score: number;
  ai_intent: string;
};

export type FunnelSummary = {
  id: string;
  name: string;
  status: string;
  description: string | null;
  steps: Array<{
    id: string;
    step_order: number;
    channel: string;
    delay_hours: number;
    message_template: string;
  }>;
  enrolled_leads: number;
};

export type ContentGenerateResult = {
  content_type: string;
  topic: string;
  mode: string;
  title?: string;
  hooks?: string[];
  body?: string;
  cta?: string;
  hashtags?: string[];
  raw?: string;
};

export type MetaConnectUrl = {
  status: string;
  url?: string;
  missing_or_placeholder_env?: string[];
};

export type MetaSyncResult = {
  instagram_account: {
    id: string;
    username: string;
  };
  media_seen: number;
  comments_created: number;
  comments_updated: number;
  automation_processed?: number;
  automation_skipped?: number;
};

export type GiveawayContent = {
  id?: string;
  automation_id?: string;
  content_type: string;
  coupon_code?: string | null;
  message_text?: string | null;
  image_url?: string | null;
  carousel_slides?: Array<Record<string, string>>;
  cta_label?: string | null;
  cta_url?: string | null;
  expires_at?: string | null;
  unique_coupon_enabled?: boolean;
  metadata_json?: Record<string, unknown>;
};

export type Giveaway = {
  id: string;
  name: string;
  status: string;
  media_id: string | null;
  media_permalink: string | null;
  trigger_type: "any_comment" | "keyword_match" | "exact_phrase";
  trigger_keywords: string[];
  public_reply_text: string;
  public_reply_variations: string[];
  dm_message_text: string;
  follow_button_text: string;
  reply_limit: number;
  cooldown_hours: number;
  exclusion_keywords: string[];
  brand_signature: string | null;
  starts_at: string | null;
  ends_at: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
  content: GiveawayContent | null;
  participant_count: number;
  reward_sent_count: number;
};

export type GiveawayCreate = Omit<Giveaway, "id" | "created_at" | "participant_count" | "reward_sent_count"> & {
  content: GiveawayContent;
};

export type GiveawayParticipant = {
  id: string;
  automation_id: string;
  instagram_user_id: string;
  instagram_username: string | null;
  comment_text: string;
  trigger_matched: string | null;
  status: string;
  reward_sent: boolean;
  error_message: string | null;
  tags: string[];
  created_at: string;
};

export type GiveawayAnalytics = {
  total_comments_captured: number;
  valid_participants: number;
  excluded_comments: number;
  dms_sent: number;
  rewards_claimed: number;
  conversion_rate: number;
  top_trigger_keywords: Array<{ keyword: string; count: number }>;
  post_performance: Array<{ automation_id: string; participants: number }>;
};

export type GiveawayDrawResult = {
  automation_id: string;
  winner_ids: string[];
  message: string;
};
