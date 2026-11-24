"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, MessageCircle, RefreshCw } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/services/api";
import type { InstagramPost } from "@/types/api";

export function InstagramPostAutomation() {
  const queryClient = useQueryClient();
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["instagram-posts"],
    queryFn: () => api.instagramPosts(24)
  });
  const [campaignByPost, setCampaignByPost] = useState<Record<string, string>>({});

  const toggle = useMutation({
    mutationFn: (args: { post: InstagramPost; campaignId: string; enabled: boolean }) =>
      api.setPostAutomation({
        media_id: args.post.id,
        permalink: args.post.permalink ?? "",
        campaign_id: args.campaignId,
        enabled: args.enabled
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["instagram-posts"] }),
        queryClient.invalidateQueries({ queryKey: ["campaigns"] })
      ]);
    }
  });

  if (isLoading) return <p className="text-sm text-[var(--muted-foreground)]">Loading your Instagram posts…</p>;
  if (error) {
    return (
      <Card>
        <CardContent className="p-4 text-sm text-[var(--danger,#b42318)]">
          {(error as Error).message || "Could not load Instagram posts. Reconnect Instagram in Settings."}
        </CardContent>
      </Card>
    );
  }

  const campaigns = data?.campaigns ?? [];
  const posts = data?.posts ?? [];
  const automatedCount = posts.filter((post) => post.automated).length;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <Badge tone={data?.scope === "all_posts" ? "warning" : "success"}>
            {data?.scope === "all_posts" ? "Replying on ALL posts" : "Selected posts only"}
          </Badge>
          <span className="text-[var(--muted-foreground)]">
            {automatedCount} of {posts.length} recent posts automated
          </span>
        </div>
        <Button variant="secondary" size="sm" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw size={14} className={isFetching ? "animate-spin" : ""} /> Refresh
        </Button>
      </div>

      {campaigns.length === 0 && (
        <Card>
          <CardContent className="p-4 text-sm">
            Create a campaign first (Campaigns page) with the public reply and DM you want sent. Then come back and switch
            it on for the posts you choose.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {posts.map((post) => {
          const linkedIds = new Set(post.campaigns.map((c) => c.id));
          const selected = campaignByPost[post.id] ?? post.campaigns[0]?.id ?? campaigns.find((c) => c.status === "active")?.id ?? "";
          const isOn = linkedIds.has(selected);
          const busy = toggle.isPending && toggle.variables?.post.id === post.id;
          return (
            <Card key={post.id} className={post.automated ? "ring-2 ring-[var(--primary)]" : undefined}>
              <div className="relative aspect-square overflow-hidden rounded-t-md bg-[var(--muted,#f4f4f5)]">
                {post.thumbnail_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={post.thumbnail_url} alt="" className="h-full w-full object-cover" loading="lazy" />
                ) : null}
                <div className="absolute left-2 top-2">
                  <Badge tone={post.automated ? "success" : "neutral"}>{post.automated ? "Automated" : "Off"}</Badge>
                </div>
              </div>
              <CardContent className="space-y-3 p-4">
                <p className="line-clamp-2 min-h-10 text-sm">{post.caption || "(no caption)"}</p>
                <div className="flex items-center justify-between text-xs text-[var(--muted-foreground)]">
                  <span className="inline-flex items-center gap-1">
                    <MessageCircle size={13} /> {post.comments_count} comments
                  </span>
                  {post.permalink && (
                    <a href={post.permalink} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 underline">
                      View <ExternalLink size={12} />
                    </a>
                  )}
                </div>

                {post.giveaway && <p className="text-xs">Giveaway running: {post.giveaway}</p>}
                {post.campaigns.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {post.campaigns.map((c) => (
                      <Badge key={c.id} tone={c.status === "active" ? "success" : "warning"}>
                        {c.name}
                        {c.status !== "active" ? ` (${c.status})` : ""}
                      </Badge>
                    ))}
                  </div>
                )}

                {campaigns.length > 0 && (
                  <div className="flex gap-2">
                    <select
                      className="h-9 min-w-0 flex-1 rounded-md border border-[var(--border)] bg-transparent px-2 text-sm"
                      value={selected}
                      onChange={(e) => setCampaignByPost((prev) => ({ ...prev, [post.id]: e.target.value }))}
                      aria-label="Campaign for this post"
                    >
                      {campaigns.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name}
                          {c.status !== "active" ? ` (${c.status})` : ""}
                        </option>
                      ))}
                    </select>
                    <Button
                      size="sm"
                      variant={isOn ? "secondary" : "primary"}
                      disabled={!selected || !post.permalink || busy}
                      onClick={() => toggle.mutate({ post, campaignId: selected, enabled: !isOn })}
                    >
                      {busy ? "Saving…" : isOn ? "Turn off" : "Automate"}
                    </Button>
                  </div>
                )}
                {isOn && post.campaigns.find((c) => c.id === selected)?.keywords.length ? (
                  <p className="text-xs text-[var(--muted-foreground)]">
                    Only comments containing: {post.campaigns.find((c) => c.id === selected)?.keywords.join(", ")}
                  </p>
                ) : null}
              </CardContent>
            </Card>
          );
        })}
      </div>
      {toggle.error && <p className="text-sm text-red-600">{(toggle.error as Error).message}</p>}
    </div>
  );
}
