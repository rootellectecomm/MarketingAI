"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/services/api";

export function CampaignForm() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [keywords, setKeywords] = useState("pcos, stress, sleep, help, details");
  const [products, setProducts] = useState("Mind Calm, PCOS Support");
  const [instagramLinks, setInstagramLinks] = useState("");
  const [publicReply, setPublicReply] = useState(true);
  const [dm, setDm] = useState(true);
  const [whatsapp, setWhatsapp] = useState(true);
  const keywordList = keywords.split(",").map((k) => k.trim()).filter(Boolean);
  const productList = products.split(",").map((p) => p.trim()).filter(Boolean);
  const targetMediaUrls = instagramLinks
    .split(/[\n,]+/)
    .map((item) => item.trim())
    .filter(Boolean);

  const mutation = useMutation({
    mutationFn: () =>
      api.createCampaign({
        name,
        status: "active",
        keyword_triggers: keywordList,
        product_focus: productList,
        public_reply_enabled: publicReply,
        dm_enabled: dm,
        whatsapp_followup_enabled: whatsapp,
        metadata_json: {
          target_media_urls: targetMediaUrls
        }
      }),
    onSuccess: async () => {
      setName("");
      await queryClient.invalidateQueries({ queryKey: ["campaigns"] });
    }
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate();
  }

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Create Reel Automation Campaign</CardTitle>
          <p className="mt-1 text-sm text-[var(--muted-foreground)]">
            Pick the comment words people type on reels, then choose exactly what the automation is allowed to send.
          </p>
        </div>
      </CardHeader>
      <CardContent>
        <form className="grid gap-4" onSubmit={onSubmit}>
          <div className="grid gap-3 md:grid-cols-3">
            <Input placeholder="Campaign name" value={name} onChange={(e) => setName(e.target.value)} required />
            <Input placeholder="Keywords (comma-separated)" value={keywords} onChange={(e) => setKeywords(e.target.value)} />
            <Input placeholder="Product focus (comma-separated)" value={products} onChange={(e) => setProducts(e.target.value)} />
          </div>
          <div>
            <label className="text-sm font-medium">Instagram reel/post links</label>
            <textarea
              className="mt-2 min-h-24 w-full rounded-md border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm outline-none transition focus:border-[var(--primary)]"
              placeholder="Paste reel/post URLs, one per line. Example: https://www.instagram.com/reel/ABC123/"
              value={instagramLinks}
              onChange={(event) => setInstagramLinks(event.target.value)}
            />
            <p className="mt-1 text-xs text-[var(--muted-foreground)]">
              Leave empty to apply this campaign to any post/reel matching the keywords.
            </p>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <label className="rounded-md border border-[var(--border)] p-3 text-sm">
              <div className="flex items-center gap-2 font-medium">
                <input type="checkbox" checked={publicReply} onChange={(e) => setPublicReply(e.target.checked)} />
                Public reel reply
              </div>
              <p className="mt-1 text-xs text-[var(--muted-foreground)]">Example: “Sent details to your DM.”</p>
            </label>
            <label className="rounded-md border border-[var(--border)] p-3 text-sm">
              <div className="flex items-center gap-2 font-medium">
                <input type="checkbox" checked={dm} onChange={(e) => setDm(e.target.checked)} />
                Private DM
              </div>
              <p className="mt-1 text-xs text-[var(--muted-foreground)]">Uses Instagram private reply on the comment.</p>
            </label>
            <label className="rounded-md border border-[var(--border)] p-3 text-sm">
              <div className="flex items-center gap-2 font-medium">
                <input type="checkbox" checked={whatsapp} onChange={(e) => setWhatsapp(e.target.checked)} />
                WhatsApp follow-up
              </div>
              <p className="mt-1 text-xs text-[var(--muted-foreground)]">Requires WhatsApp credentials and opt-in data.</p>
            </label>
          </div>

          <div className="grid gap-3 rounded-md border border-[var(--border)] bg-[var(--muted)] p-3 md:grid-cols-2">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">Trigger words</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {keywordList.map((keyword) => (
                  <Badge key={keyword}>{keyword}</Badge>
                ))}
              </div>
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">Products in AI context</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {productList.map((product) => (
                  <Badge key={product} tone="success">
                    {product}
                  </Badge>
                ))}
              </div>
            </div>
            <div className="md:col-span-2">
              <div className="text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">Targeted reels/posts</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {targetMediaUrls.length ? (
                  targetMediaUrls.map((url) => (
                    <Badge key={url} tone="warning">
                      {url}
                    </Badge>
                  ))
                ) : (
                  <Badge>All media</Badge>
                )}
              </div>
            </div>
          </div>

          {mutation.error ? (
            <div className="rounded-md border border-[var(--danger)] p-3 text-sm text-[var(--danger)]">
              {mutation.error instanceof Error ? mutation.error.message : "Could not create campaign."}
            </div>
          ) : null}

          <Button type="submit" disabled={mutation.isPending || !name.trim() || keywordList.length === 0}>
            {mutation.isPending ? "Creating…" : "Create active automation"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
