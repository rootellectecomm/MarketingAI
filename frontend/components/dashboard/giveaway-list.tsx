"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pause, Play, Trophy } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/services/api";
import type { Giveaway, GiveawayCreate } from "@/types/api";

export function GiveawayList() {
  const queryClient = useQueryClient();
  const { data: giveaways = [] } = useQuery({ queryKey: ["giveaways"], queryFn: api.giveaways });
  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<GiveawayCreate> }) => api.updateGiveaway(id, payload),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["giveaways"] })
  });
  const drawMutation = useMutation({
    mutationFn: (id: string) => api.drawGiveaway(id),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["giveaways"] }),
        queryClient.invalidateQueries({ queryKey: ["giveaway-analytics"] })
      ]);
    }
  });

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      {giveaways.map((giveaway) => (
        <Card key={giveaway.id}>
          <CardHeader>
            <div>
              <CardTitle>{giveaway.name}</CardTitle>
              <p className="mt-1 max-w-xl truncate text-sm text-[var(--muted-foreground)]">
                {giveaway.media_permalink || giveaway.media_id || "No post selected"}
              </p>
            </div>
            <Badge tone={giveaway.status === "active" ? "success" : "neutral"}>{giveaway.status}</Badge>
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="flex flex-wrap gap-2">
              {giveaway.trigger_keywords.map((keyword) => (
                <Badge key={keyword}>{keyword}</Badge>
              ))}
            </div>
            <div className="grid gap-3 text-sm md:grid-cols-4">
              <Stat label="Participants" value={giveaway.participant_count} />
              <Stat label="Rewards sent" value={giveaway.reward_sent_count} />
              <Stat label="Reply limit" value={giveaway.reply_limit} />
              <Stat label="Trigger" value={giveaway.trigger_type.replace("_", " ")} />
            </div>
            <div className="rounded-md border border-[var(--border)] p-3 text-sm">
              <div className="font-medium">DM flow</div>
              <p className="mt-1 text-[var(--muted-foreground)]">{giveaway.dm_message_text}</p>
              <p className="mt-2 text-[var(--muted-foreground)]">
                Reward: {giveaway.content?.coupon_code || giveaway.content?.cta_url || giveaway.content?.message_text || "Not configured"}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                variant={giveaway.status === "active" ? "secondary" : "primary"}
                onClick={() =>
                  updateMutation.mutate({
                    id: giveaway.id,
                    payload: { status: giveaway.status === "active" ? "paused" : "active" }
                  })
                }
              >
                {giveaway.status === "active" ? <Pause size={14} /> : <Play size={14} />}
                {giveaway.status === "active" ? "Pause" : "Activate"}
              </Button>
              <Button type="button" size="sm" variant="secondary" onClick={() => drawMutation.mutate(giveaway.id)}>
                <Trophy size={14} />
                Draw winner
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
      {!giveaways.length ? (
        <Card>
          <CardContent className="pt-5 text-sm text-[var(--muted-foreground)]">
            No giveaway automations yet. Create one above to start capturing reel/post comments.
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md border border-[var(--border)] p-3">
      <div className="text-xs text-[var(--muted-foreground)]">{label}</div>
      <div className="font-semibold">{value}</div>
    </div>
  );
}
