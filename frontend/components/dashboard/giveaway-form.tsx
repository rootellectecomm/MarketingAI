"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/services/api";
import type { GiveawayCreate } from "@/types/api";

const defaults = {
  name: "Mind Calm giveaway",
  media_permalink: "",
  trigger_type: "keyword_match" as const,
  trigger_keywords: "calm, sleep, stress, overthinking",
  public_reply_text: "Thanks for joining. Please check your DM.",
  dm_message_text: "You're in. Follow Rootellect and reply I have followed to receive your Mind Calm wellness guide.",
  coupon_code: "MINDCALM10",
  reward_message: "Here is your Mind Calm sleep routine and giveaway coupon.",
  cta_url: "https://rootellect.com"
};

export function GiveawayForm() {
  const queryClient = useQueryClient();
  const { data: templates = [] } = useQuery({ queryKey: ["giveaway-templates"], queryFn: api.giveawayTemplates });
  const [form, setForm] = useState(defaults);
  const keywords = form.trigger_keywords.split(",").map((item) => item.trim()).filter(Boolean);
  const mutation = useMutation({
    mutationFn: () => api.createGiveaway(buildPayload(form, keywords)),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["giveaways"] }),
        queryClient.invalidateQueries({ queryKey: ["giveaway-analytics"] })
      ]);
    }
  });

  function update(key: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function applyTemplate(template: Partial<GiveawayCreate>) {
    setForm((current) => ({
      ...current,
      name: template.name ?? current.name,
      trigger_keywords: template.trigger_keywords?.join(", ") ?? current.trigger_keywords,
      public_reply_text: template.public_reply_text ?? current.public_reply_text,
      dm_message_text: template.dm_message_text ?? current.dm_message_text,
      coupon_code: template.content?.coupon_code ?? current.coupon_code,
      reward_message: template.content?.message_text ?? current.reward_message,
      cta_url: template.content?.cta_url ?? current.cta_url
    }));
  }

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Create Giveaway Automation</CardTitle>
          <p className="mt-1 text-sm text-[var(--muted-foreground)]">
            Step-by-step Interakt-style flow: post, trigger, public reply, follow-confirm DM, reward delivery.
          </p>
        </div>
      </CardHeader>
      <CardContent>
        <div className="mb-4 flex flex-wrap gap-2">
          {templates.map((template) => (
            <Button key={template.name} type="button" variant="secondary" size="sm" onClick={() => applyTemplate(template)}>
              Use {template.name}
            </Button>
          ))}
        </div>
        <form
          className="grid gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            mutation.mutate();
          }}
        >
          <div className="grid gap-3 md:grid-cols-2">
            <Input value={form.name} onChange={(event) => update("name", event.target.value)} placeholder="Automation name" />
            <Input
              value={form.media_permalink}
              onChange={(event) => update("media_permalink", event.target.value)}
              placeholder="Instagram reel/post URL"
            />
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <select
              value={form.trigger_type}
              onChange={(event) => update("trigger_type", event.target.value)}
              className="h-10 rounded-md border border-[var(--border)] bg-[var(--card)] px-3 text-sm"
            >
              <option value="any_comment">Any comment</option>
              <option value="keyword_match">Keyword match</option>
              <option value="exact_phrase">Exact phrase match</option>
            </select>
            <Input
              className="md:col-span-2"
              value={form.trigger_keywords}
              onChange={(event) => update("trigger_keywords", event.target.value)}
              placeholder="Trigger keywords"
            />
          </div>
          <textarea
            className="min-h-20 rounded-md border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm"
            value={form.public_reply_text}
            onChange={(event) => update("public_reply_text", event.target.value)}
            placeholder="Public comment reply"
          />
          <textarea
            className="min-h-24 rounded-md border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm"
            value={form.dm_message_text}
            onChange={(event) => update("dm_message_text", event.target.value)}
            placeholder="DM follow-confirm message"
          />
          <div className="grid gap-3 md:grid-cols-3">
            <Input value={form.coupon_code} onChange={(event) => update("coupon_code", event.target.value)} placeholder="Coupon code" />
            <Input value={form.cta_url} onChange={(event) => update("cta_url", event.target.value)} placeholder="CTA / reward link" />
            <Input value="I have followed" disabled />
          </div>
          <textarea
            className="min-h-20 rounded-md border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm"
            value={form.reward_message}
            onChange={(event) => update("reward_message", event.target.value)}
            placeholder="Reward message"
          />
          <div className="rounded-md border border-[var(--border)] p-3">
            <div className="mb-2 text-sm font-medium">Preview</div>
            <div className="grid gap-3 md:grid-cols-3">
              <Preview title="Comment trigger" body={keywords.join(", ") || "Any comment"} />
              <Preview title="Public reply" body={form.public_reply_text} />
              <Preview title="DM + reward" body={`${form.dm_message_text}\n\nButton: I have followed\n\nReward: ${form.coupon_code}`} />
            </div>
          </div>
          {mutation.error ? (
            <div className="rounded-md border border-[var(--danger)] p-3 text-sm text-[var(--danger)]">
              {mutation.error instanceof Error ? mutation.error.message : "Could not create giveaway."}
            </div>
          ) : null}
          <Button type="submit" disabled={mutation.isPending || !form.name.trim()}>
            {mutation.isPending ? "Creating…" : "Review and activate"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function Preview({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-md bg-[var(--muted)] p-3 text-sm">
      <Badge>{title}</Badge>
      <p className="mt-2 whitespace-pre-line text-[var(--muted-foreground)]">{body}</p>
    </div>
  );
}

function buildPayload(form: typeof defaults, keywords: string[]): GiveawayCreate {
  return {
    name: form.name,
    status: "active",
    media_id: null,
    media_permalink: form.media_permalink || null,
    trigger_type: form.trigger_type,
    trigger_keywords: keywords,
    public_reply_text: form.public_reply_text,
    public_reply_variations: [],
    dm_message_text: form.dm_message_text,
    follow_button_text: "I have followed",
    reply_limit: 500,
    cooldown_hours: 24,
    exclusion_keywords: ["fake", "scam", "not interested", "bad", "stop"],
    brand_signature: "Rootellect",
    starts_at: null,
    ends_at: null,
    metadata_json: {},
    content: {
      content_type: "coupon",
      coupon_code: form.coupon_code,
      message_text: form.reward_message,
      cta_label: "Open reward",
      cta_url: form.cta_url
    }
  };
}
