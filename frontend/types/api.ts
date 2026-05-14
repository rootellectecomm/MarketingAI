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

