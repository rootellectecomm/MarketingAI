"use client";

import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/services/api";

export function GiveawayParticipantsTable() {
  const { data: giveaways = [] } = useQuery({ queryKey: ["giveaways"], queryFn: api.giveaways });
  const active = giveaways[0];
  const { data: participants = [] } = useQuery({
    queryKey: ["giveaway-participants", active?.id],
    queryFn: () => api.giveawayParticipants(active?.id ?? ""),
    enabled: Boolean(active?.id)
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Participant CRM</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-[var(--muted-foreground)]">
              <tr>
                <th className="py-2">Username</th>
                <th className="py-2">Comment</th>
                <th className="py-2">Trigger</th>
                <th className="py-2">Status</th>
                <th className="py-2">Reward</th>
                <th className="py-2">Tags</th>
              </tr>
            </thead>
            <tbody>
              {participants.map((participant) => (
                <tr key={participant.id} className="border-t border-[var(--border)]">
                  <td className="py-3">{participant.instagram_username ?? participant.instagram_user_id}</td>
                  <td className="max-w-xs truncate py-3">{participant.comment_text}</td>
                  <td className="py-3">{participant.trigger_matched ?? "-"}</td>
                  <td className="py-3">
                    <Badge tone={participant.status === "reward_sent" ? "success" : "neutral"}>{participant.status}</Badge>
                  </td>
                  <td className="py-3">{participant.reward_sent ? "Sent" : "Pending"}</td>
                  <td className="py-3">
                    <div className="flex flex-wrap gap-1">
                      {participant.tags.map((tag) => (
                        <Badge key={tag}>{tag}</Badge>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!participants.length ? (
            <p className="py-6 text-sm text-[var(--muted-foreground)]">
              No participants yet. Sync comments after your giveaway post receives comments.
            </p>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
