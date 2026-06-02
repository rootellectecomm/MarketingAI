"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Gift, MessageCircle, RefreshCw, Send, Trophy } from "lucide-react";
import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/services/api";

export function GiveawayCommandCenter() {
  const queryClient = useQueryClient();
  const { data: analytics } = useQuery({ queryKey: ["giveaway-analytics"], queryFn: api.giveawayAnalytics });
  const { data: providers } = useQuery({ queryKey: ["providers"], queryFn: api.providerStatus });
  const syncMutation = useMutation({
    mutationFn: () => api.syncMetaComments({ media_limit: 50, comments_per_media: 50 }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["giveaways"] }),
        queryClient.invalidateQueries({ queryKey: ["giveaway-analytics"] }),
        queryClient.invalidateQueries({ queryKey: ["comments"] })
      ]);
    }
  });

  return (
    <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
      <Card>
        <CardHeader>
          <div>
            <CardTitle>Giveaway Automation Command Center</CardTitle>
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">
              Capture comments, send public replies, DM follow confirmation, and deliver rewards from one workflow.
            </p>
          </div>
          <Badge tone={providers?.instagram_ready ? "success" : "warning"}>
            {providers?.instagram_ready ? "Instagram connected" : "Connect Instagram"}
          </Badge>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="grid gap-3 md:grid-cols-5">
            <Metric icon={<MessageCircle size={16} />} label="Captured" value={analytics?.total_comments_captured ?? 0} />
            <Metric icon={<Gift size={16} />} label="Participants" value={analytics?.valid_participants ?? 0} />
            <Metric icon={<Send size={16} />} label="DMs sent" value={analytics?.dms_sent ?? 0} />
            <Metric icon={<Trophy size={16} />} label="Rewards" value={analytics?.rewards_claimed ?? 0} />
            <Metric label="Conversion" value={`${analytics?.conversion_rate ?? 0}%`} />
          </div>
          <div className="flex flex-wrap items-center gap-3 rounded-md border border-[var(--border)] p-3">
            <Button type="button" onClick={() => syncMutation.mutate()} disabled={syncMutation.isPending}>
              <RefreshCw size={16} />
              {syncMutation.isPending ? "Processing comments" : "Sync comments + process entries"}
            </Button>
            <span className="text-sm text-[var(--muted-foreground)]">
              Use after creating an automation or pasting a new reel/post link.
            </span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Top Triggers</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {(analytics?.top_trigger_keywords ?? []).map((item) => (
            <div key={item.keyword} className="flex items-center justify-between rounded-md border border-[var(--border)] px-3 py-2">
              <span className="text-sm">{item.keyword}</span>
              <Badge tone="success">{item.count}</Badge>
            </div>
          ))}
          {!analytics?.top_trigger_keywords?.length ? (
            <p className="text-sm text-[var(--muted-foreground)]">No triggers captured yet.</p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

function Metric({ icon, label, value }: { icon?: ReactNode; label: string; value: string | number }) {
  return (
    <div className="rounded-md border border-[var(--border)] p-3">
      <div className="flex items-center gap-2 text-xs text-[var(--muted-foreground)]">{icon}{label}</div>
      <div className="mt-2 text-xl font-semibold">{value}</div>
    </div>
  );
}
