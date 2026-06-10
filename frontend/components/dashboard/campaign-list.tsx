"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, MessageSquareText, Power, Send } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/services/api";
import type { Campaign } from "@/types/api";

export function CampaignList() {
  const queryClient = useQueryClient();
  const [linkDrafts, setLinkDrafts] = useState<Record<string, string>>({});
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
  const { data = [] } = useQuery({ queryKey: ["campaigns"], queryFn: api.campaigns });
  const selectedId = selectedCampaignId ?? data[0]?.id ?? "";
  const { data: events = [] } = useQuery({
    queryKey: ["campaign-events", selectedId],
    queryFn: () => api.campaignEvents(selectedId),
    enabled: Boolean(selectedId)
  });
  const mutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<Campaign> }) => api.updateCampaign(id, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["campaigns"] });
    }
  });

  function update(campaign: Campaign, payload: Partial<Campaign>) {
    mutation.mutate({ id: campaign.id, payload });
  }

  function saveTargetLinks(campaign: Campaign) {
    const current = campaign.metadata_json?.target_media_urls?.join("\n") ?? "";
    const targetMediaUrls = (linkDrafts[campaign.id] ?? current)
      .split(/[\n,]+/)
      .map((item) => item.trim())
      .filter(Boolean);
    update(campaign, {
      metadata_json: {
        ...campaign.metadata_json,
        target_media_urls: targetMediaUrls
      }
    });
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {data.map((campaign) => {
        const targetUrls = campaign.metadata_json?.target_media_urls ?? [];
        const resolvedIds = campaign.metadata_json?.target_media_ids ?? [];
        const campaignEvents = selectedId === campaign.id ? events : [];
        const dmSent = campaignEvents.filter((event) => event.status === "dm_sent").length;
        const matched = campaignEvents.filter((event) => event.status !== "duplicate_skipped").length;
        const latestStage = campaignEvents[0]?.status ?? "no activity";
        return (
        <Card key={campaign.id} className={campaign.status !== "active" ? "opacity-75" : undefined}>
          <CardHeader>
            <div>
              <CardTitle>{campaign.name}</CardTitle>
              <div className="mt-1 text-sm text-[var(--muted-foreground)]">
                {campaign.product_name ?? campaign.product_focus.join(", ")} · {campaign.platform}
              </div>
            </div>
            <Badge tone={campaign.status === "active" ? "success" : "neutral"}>{campaign.status}</Badge>
          </CardHeader>
          <CardContent>
            <div className="mb-4 flex flex-wrap gap-2">
              {campaign.keyword_triggers.map((keyword) => (
                <Badge key={keyword}>{keyword}</Badge>
              ))}
            </div>
            <div className="mb-4 grid gap-2 text-sm md:grid-cols-2">
              <InfoLine label="Product link" value={campaign.product_link ?? "Not set"} />
              <InfoLine label="WhatsApp" value={campaign.whatsapp_link ?? "Default Rootellect link"} />
            </div>
            <div className="mb-4 rounded-md border border-[var(--border)] p-3">
              <div className="text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">
                Target reels/posts
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {targetUrls.length ? (
                  targetUrls.map((url) => (
                    <Badge key={url} tone={resolvedIds.length ? "success" : "warning"}>
                      {resolvedIds.length ? "Resolved" : "Waiting for sync"} · {url}
                    </Badge>
                  ))
                ) : (
                  <Badge>All reels/posts with trigger keywords</Badge>
                )}
              </div>
              <textarea
                className="mt-3 min-h-20 w-full rounded-md border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm outline-none transition focus:border-[var(--primary)]"
                value={linkDrafts[campaign.id] ?? targetUrls.join("\n")}
                onChange={(event) => setLinkDrafts((current) => ({ ...current, [campaign.id]: event.target.value }))}
                placeholder="Paste reel/post links to target this campaign"
              />
              <Button type="button" variant="secondary" size="sm" className="mt-2" onClick={() => saveTargetLinks(campaign)}>
                Save target links
              </Button>
            </div>
            <div className="grid gap-3 text-sm sm:grid-cols-3">
              <button
                type="button"
                onClick={() => update(campaign, { public_reply_enabled: !campaign.public_reply_enabled })}
                className="flex items-center gap-2 rounded-md border border-[var(--border)] p-3 text-left hover:bg-[var(--muted)]"
              >
                <MessageSquareText size={16} className="text-[var(--primary)]" />
                {campaign.public_reply_enabled ? "Public replies on" : "Public replies off"}
              </button>
              <button
                type="button"
                onClick={() => update(campaign, { dm_enabled: !campaign.dm_enabled })}
                className="flex items-center gap-2 rounded-md border border-[var(--border)] p-3 text-left hover:bg-[var(--muted)]"
              >
                <Send size={16} className="text-[var(--primary)]" />
                {campaign.dm_enabled ? "DMs on" : "DMs off"}
              </button>
              <button
                type="button"
                onClick={() => update(campaign, { whatsapp_followup_enabled: !campaign.whatsapp_followup_enabled })}
                className="flex items-center gap-2 rounded-md border border-[var(--border)] p-3 text-left hover:bg-[var(--muted)]"
              >
                <Bot size={16} className="text-[var(--primary)]" />
                {campaign.whatsapp_followup_enabled ? "WhatsApp follow-up" : "No WA follow-up"}
              </button>
              <button
                type="button"
                onClick={() => update(campaign, { ai_followup_enabled: !campaign.ai_followup_enabled })}
                className="flex items-center gap-2 rounded-md border border-[var(--border)] p-3 text-left hover:bg-[var(--muted)]"
              >
                <Bot size={16} className="text-[var(--primary)]" />
                {campaign.ai_followup_enabled ? "AI follow-up on" : "AI follow-up off"}
              </button>
            </div>

            <div className="mt-4 grid gap-3 rounded-md border border-[var(--border)] p-3 text-sm md:grid-cols-4">
              <div>
                <div className="text-xs text-[var(--muted-foreground)]">Matched comments</div>
                <div className="font-medium">{selectedId === campaign.id ? matched : "Select"}</div>
              </div>
              <div>
                <div className="text-xs text-[var(--muted-foreground)]">DMs sent</div>
                <div className="font-medium">{selectedId === campaign.id ? dmSent : "Select"}</div>
              </div>
              <div>
                <div className="text-xs text-[var(--muted-foreground)]">Send channels</div>
                <div className="font-medium">
                  {[campaign.public_reply_enabled && "Reply", campaign.dm_enabled && "DM", campaign.whatsapp_followup_enabled && "WA"]
                    .filter(Boolean)
                    .join(" + ") || "Paused"}
                </div>
              </div>
              <div>
                <div className="text-xs text-[var(--muted-foreground)]">Conversion stage</div>
                <div className="font-medium">{selectedId === campaign.id ? latestStage : campaign.status}</div>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              <Button
                type="button"
                variant={campaign.status === "active" ? "secondary" : "primary"}
                size="sm"
                onClick={() => update(campaign, { status: campaign.status === "active" ? "paused" : "active" })}
              >
                <Power size={14} />
                {campaign.status === "active" ? "Pause automation" : "Go live"}
              </Button>
              <Button type="button" variant="secondary" size="sm" onClick={() => setSelectedCampaignId(campaign.id)}>
                View activity
              </Button>
            </div>

            {selectedId === campaign.id && campaignEvents.length ? (
              <div className="mt-4 overflow-hidden rounded-md border border-[var(--border)] text-sm">
                {campaignEvents.slice(0, 5).map((event) => (
                  <div key={event.id} className="grid gap-2 border-b border-[var(--border)] p-3 last:border-b-0 md:grid-cols-4">
                    <div>
                      <div className="text-xs text-[var(--muted-foreground)]">Keyword</div>
                      <div className="font-medium">{event.matched_keyword ?? "-"}</div>
                    </div>
                    <div>
                      <div className="text-xs text-[var(--muted-foreground)]">User</div>
                      <div className="font-medium">{event.username ?? event.user_id ?? "-"}</div>
                    </div>
                    <div>
                      <div className="text-xs text-[var(--muted-foreground)]">Intent</div>
                      <div className="font-medium">{event.ai_intent ?? "-"}</div>
                    </div>
                    <div>
                      <div className="text-xs text-[var(--muted-foreground)]">Status</div>
                      <Badge tone={event.status === "dm_sent" ? "success" : "neutral"}>{event.status}</Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </CardContent>
        </Card>
        );
      })}
      {data.length === 0 ? (
        <Card>
          <CardContent className="pt-5 text-sm text-[var(--muted-foreground)]">
            No campaigns yet. Create one with keywords like “details” or “help” to start reel comment automation.
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

function InfoLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-[var(--border)] p-3">
      <div className="text-xs text-[var(--muted-foreground)]">{label}</div>
      <div className="truncate font-medium">{value}</div>
    </div>
  );
}
