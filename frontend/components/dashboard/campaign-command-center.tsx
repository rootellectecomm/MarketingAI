"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, RefreshCw, Send, ShieldAlert, Zap } from "lucide-react";
import type { ReactNode } from "react";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/services/api";

export function CampaignCommandCenter() {
  const queryClient = useQueryClient();
  const [testComment, setTestComment] = useState("details");
  const { data: campaigns = [] } = useQuery({ queryKey: ["campaigns"], queryFn: api.campaigns });
  const { data: comments = [] } = useQuery({ queryKey: ["comments"], queryFn: api.comments });
  const { data: providers } = useQuery({ queryKey: ["providers"], queryFn: api.providerStatus });
  const { data: aiLogs = [] } = useQuery({ queryKey: ["ai-logs"], queryFn: api.aiLogs });
  const syncMutation = useMutation({
    mutationFn: () => api.syncMetaComments({ media_limit: 50, comments_per_media: 50 }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["comments"] }),
        queryClient.invalidateQueries({ queryKey: ["metrics"] }),
        queryClient.invalidateQueries({ queryKey: ["leads"] }),
        queryClient.invalidateQueries({ queryKey: ["ai-logs"] }),
        queryClient.invalidateQueries({ queryKey: ["webhooks"] })
      ]);
    }
  });

  const liveCampaigns = campaigns.filter((campaign) => campaign.status === "active");
  const targetedCampaigns = liveCampaigns.filter((campaign) => campaign.metadata_json?.target_media_urls?.length);
  const matchedCampaigns = useMemo(() => {
    const normalized = testComment.toLowerCase();
    return liveCampaigns.filter((campaign) =>
      campaign.keyword_triggers.some((keyword) => normalized.includes(keyword.toLowerCase()))
    );
  }, [liveCampaigns, testComment]);
  const privateReplies = comments.filter((comment) => comment.private_replied).length;
  const publicReplies = comments.filter((comment) => comment.replied).length;
  const blockedAi = aiLogs.filter((log) => Boolean(log.blocked)).length;

  return (
    <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
      <Card>
        <CardHeader>
          <div>
            <CardTitle>Automation Command Center</CardTitle>
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">
              End-to-end workflow for reel comments: trigger word → AI decision → public reply → private DM.
            </p>
          </div>
          <Badge tone={providers?.instagram_ready ? "success" : "warning"}>
            {providers?.instagram_ready ? "Instagram connected" : "Instagram not ready"}
          </Badge>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="grid gap-3 md:grid-cols-4">
            <WorkflowStep
              icon={<Zap size={16} />}
              label="1. Trigger"
              value={`${liveCampaigns.length} active · ${targetedCampaigns.length} linked`}
              ok={liveCampaigns.length > 0}
            />
            <WorkflowStep
              icon={<ShieldAlert size={16} />}
              label="2. Safety + AI"
              value={providers?.openai_ready ? "OpenAI ready" : "Fallback mode"}
              ok={providers?.openai_ready ?? false}
            />
            <WorkflowStep
              icon={<Send size={16} />}
              label="3. Private DM"
              value={`${privateReplies} sent`}
              ok={privateReplies > 0}
            />
            <WorkflowStep
              icon={<CheckCircle2 size={16} />}
              label="4. Tracking"
              value={`${comments.length} comments`}
              ok={comments.length > 0}
            />
          </div>

          <div className="grid gap-3 rounded-md border border-[var(--border)] p-3 md:grid-cols-[1fr_auto] md:items-end">
            <div>
              <label className="text-sm font-medium">Test a reel comment before posting</label>
              <Input value={testComment} onChange={(event) => setTestComment(event.target.value)} className="mt-2" />
              <div className="mt-2 flex flex-wrap gap-2 text-sm">
                {matchedCampaigns.length ? (
                  matchedCampaigns.map((campaign) => (
                    <Badge key={campaign.id} tone="success">
                      Matches {campaign.name}
                    </Badge>
                  ))
                ) : (
                  <Badge tone="warning">No active campaign matches this text</Badge>
                )}
              </div>
            </div>
            <Button type="button" onClick={() => syncMutation.mutate()} disabled={syncMutation.isPending}>
              <RefreshCw size={16} />
              {syncMutation.isPending ? "Processing comments" : "Sync + run automation"}
            </Button>
          </div>

          {syncMutation.data ? (
            <div className="rounded-md border border-[var(--success)] p-3 text-sm text-[var(--success)]">
              Synced {syncMutation.data.comments_created} new and {syncMutation.data.comments_updated} existing comments.
              Automation sent or updated {syncMutation.data.automation_processed ?? 0}; skipped{" "}
              {syncMutation.data.automation_skipped ?? 0}.
            </div>
          ) : null}
          {syncMutation.error ? (
            <div className="rounded-md border border-[var(--danger)] p-3 text-sm text-[var(--danger)]">
              {syncMutation.error instanceof Error ? syncMutation.error.message : "Comment sync failed."}
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Automation Health</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <HealthRow label="Provider mode" value={providers?.provider_mode ?? "unknown"} ok={providers?.provider_mode !== "mock"} />
          <HealthRow label="Facebook ready" value={providers?.facebook_ready ? "yes" : "no"} ok={providers?.facebook_ready ?? false} />
          <HealthRow label="Instagram ready" value={providers?.instagram_ready ? "yes" : "no"} ok={providers?.instagram_ready ?? false} />
          <HealthRow label="Public replies sent" value={String(publicReplies)} ok={publicReplies > 0} />
          <HealthRow label="Private DMs sent" value={String(privateReplies)} ok={privateReplies > 0} />
          <HealthRow label="AI blocked / review" value={String(blockedAi)} ok={blockedAi === 0} />
          {providers?.setup_warnings?.length ? (
            <div className="rounded-md border border-[var(--warning)] p-3 text-[var(--warning)]">
              {providers.setup_warnings.join(" ")}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

function WorkflowStep({
  icon,
  label,
  value,
  ok
}: {
  icon: ReactNode;
  label: string;
  value: string;
  ok: boolean;
}) {
  return (
    <div className="rounded-md border border-[var(--border)] p-3">
      <div className={ok ? "text-[var(--success)]" : "text-[var(--warning)]"}>{icon}</div>
      <div className="mt-2 text-xs text-[var(--muted-foreground)]">{label}</div>
      <div className="font-semibold">{value}</div>
    </div>
  );
}

function HealthRow({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-[var(--border)] px-3 py-2">
      <span className="text-[var(--muted-foreground)]">{label}</span>
      <Badge tone={ok ? "success" : "warning"}>{value}</Badge>
    </div>
  );
}
