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
  lifecycle_stage: string;
  phone: string | null;
  whatsapp_opt_in: boolean;
  score: number;
  tags: string[];
  created_at: string;
};

export type Campaign = {
  id: string;
  name: string;
  status: string;
  product_focus: string[];
  keyword_triggers: string[];
  public_reply_enabled: boolean;
  dm_enabled: boolean;
  whatsapp_followup_enabled: boolean;
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
  product_focus?: string[];
  keyword_triggers?: string[];
  public_reply_enabled?: boolean;
  dm_enabled?: boolean;
  whatsapp_followup_enabled?: boolean;
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
};
