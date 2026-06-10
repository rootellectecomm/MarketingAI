"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/services/api";

const PRODUCT_OPTIONS = [
  {
    name: "Mind Calm",
    key: "mind_calm",
    link: "https://www.rootellect.com/products/mind-calm",
    keywords: "stress, sleep, overthinking, mind calm, link, price, tired, anxiety, brain fog",
    dm:
      "Got it. Mind Calm is the closest fit if your concern is stress, overthinking or sleep quality. " +
      "It's non-melatonin and supports calmness + better sleep quality. {{product_link}}"
  },
  {
    name: "Women Balance",
    key: "women_balance",
    link: "https://www.rootellect.com/products/women-balance",
    keywords: "women, pms, periods, fatigue, mood, energy, monthly wellness",
    dm:
      "This sounds more like PMS + energy support. Women Balance fits better - it supports daily women's " +
      "hormonal wellness, mood and energy. {{product_link}}"
  },
  {
    name: "PCOS Support",
    key: "pcos_support",
    link: "https://www.rootellect.com/products/pcos-pcod-support",
    keywords: "pcos, pcod, irregular periods, acne, facial hair, cravings, cycle",
    dm:
      "For PCOS/PCOD wellness, PCOS Support is the most relevant option. It's a non-hormonal formula designed " +
      "to support cycle wellness, hormonal balance, skin concerns and metabolic health. {{product_link}}"
  },
  {
    name: "Perimenopause Support",
    key: "perimenopause_support",
    link: "https://www.rootellect.com/products/perimenopause-support",
    keywords: "35+, hot flashes, perimenopause, menopause, mood shifts, sleep changes",
    dm:
      "If she's around 35+ or in the transition phase, Perimenopause Support is the closest fit. It's designed " +
      "to support hot flashes, mood, sleep and hormonal transition comfort. {{product_link}}"
  }
];

const DEFAULT_WHATSAPP_LINK =
  "https://wa.me/918679508311?text=Hi%20Rootellect%2C%20I%20want%20to%20know%20about%20Mind%20Calm";

export function CampaignForm() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("Mind Calm Stress Campaign");
  const [platform, setPlatform] = useState("both");
  const [postId, setPostId] = useState("");
  const [productName, setProductName] = useState("Mind Calm");
  const selectedProduct = useMemo(
    () => PRODUCT_OPTIONS.find((product) => product.name === productName) ?? PRODUCT_OPTIONS[0],
    [productName]
  );
  const [keywords, setKeywords] = useState(selectedProduct.keywords);
  const [productLink, setProductLink] = useState(selectedProduct.link);
  const [followupLink, setFollowupLink] = useState(selectedProduct.link);
  const [whatsappLink, setWhatsappLink] = useState(DEFAULT_WHATSAPP_LINK);
  const [publicReplyTemplate, setPublicReplyTemplate] = useState("Sent you the details in DM.");
  const [dmTemplate, setDmTemplate] = useState(selectedProduct.dm);
  const [instagramLinks, setInstagramLinks] = useState("");
  const [publicReply, setPublicReply] = useState(true);
  const [dm, setDm] = useState(true);
  const [whatsapp, setWhatsapp] = useState(true);
  const [aiFollowup, setAiFollowup] = useState(true);
  const keywordList = keywords.split(",").map((k) => k.trim()).filter(Boolean);
  const targetMediaUrls = instagramLinks
    .split(/[\n,]+/)
    .map((item) => item.trim())
    .filter(Boolean);

  function applyProduct(product: string) {
    const next = PRODUCT_OPTIONS.find((item) => item.name === product) ?? PRODUCT_OPTIONS[0];
    setProductName(next.name);
    setKeywords(next.keywords);
    setProductLink(next.link);
    setFollowupLink(next.link);
    setDmTemplate(next.dm);
    setWhatsappLink(
      next.name === "Mind Calm"
        ? DEFAULT_WHATSAPP_LINK
        : `https://wa.me/918679508311?text=Hi%20Rootellect%2C%20I%20want%20to%20know%20about%20${encodeURIComponent(next.name)}`
    );
  }

  const mutation = useMutation({
    mutationFn: () =>
      api.createCampaign({
        name,
        status: "active",
        platform,
        post_id: postId.trim() || null,
        product_key: selectedProduct.key,
        product_name: productName,
        product_link: productLink,
        followup_link: followupLink,
        whatsapp_link: whatsappLink,
        keyword_triggers: keywordList,
        product_focus: [productName],
        public_reply_template: publicReplyTemplate,
        dm_template: dmTemplate,
        public_reply_enabled: publicReply,
        dm_enabled: dm,
        whatsapp_followup_enabled: whatsapp,
        ai_followup_enabled: aiFollowup,
        metadata_json: {
          target_media_urls: targetMediaUrls
        }
      }),
    onSuccess: async () => {
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
          <CardTitle>Create Conversion Campaign</CardTitle>
          <p className="mt-1 text-sm text-[var(--muted-foreground)]">
            Configure comment keywords, product links, DM copy, and WhatsApp continuation for a live product campaign.
          </p>
        </div>
      </CardHeader>
      <CardContent>
        <form className="grid gap-4" onSubmit={onSubmit}>
          <div className="grid gap-3 md:grid-cols-4">
            <Input placeholder="Campaign name" value={name} onChange={(e) => setName(e.target.value)} required />
            <select
              className="rounded-md border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm outline-none"
              value={platform}
              onChange={(event) => setPlatform(event.target.value)}
            >
              <option value="both">Instagram + Facebook</option>
              <option value="instagram">Instagram</option>
              <option value="facebook">Facebook</option>
            </select>
            <Input placeholder="Post/media ID (optional)" value={postId} onChange={(e) => setPostId(e.target.value)} />
            <select
              className="rounded-md border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm outline-none"
              value={productName}
              onChange={(event) => applyProduct(event.target.value)}
            >
              {PRODUCT_OPTIONS.map((product) => (
                <option key={product.key} value={product.name}>
                  {product.name}
                </option>
              ))}
            </select>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <Input placeholder="Product link" value={productLink} onChange={(e) => setProductLink(e.target.value)} />
            <Input placeholder="Follow-up link" value={followupLink} onChange={(e) => setFollowupLink(e.target.value)} />
            <Input placeholder="WhatsApp link" value={whatsappLink} onChange={(e) => setWhatsappLink(e.target.value)} />
          </div>

          <Input placeholder="Keywords (comma-separated)" value={keywords} onChange={(e) => setKeywords(e.target.value)} />

          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <label className="text-sm font-medium">Public comment reply</label>
              <textarea
                className="mt-2 min-h-20 w-full rounded-md border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm outline-none"
                value={publicReplyTemplate}
                onChange={(event) => setPublicReplyTemplate(event.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium">DM reply</label>
              <textarea
                className="mt-2 min-h-20 w-full rounded-md border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm outline-none"
                value={dmTemplate}
                onChange={(event) => setDmTemplate(event.target.value)}
              />
            </div>
          </div>

          <div>
            <label className="text-sm font-medium">Instagram/Facebook post links</label>
            <textarea
              className="mt-2 min-h-20 w-full rounded-md border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm outline-none"
              placeholder="Paste reel/post URLs, one per line. Leave empty for all matching posts."
              value={instagramLinks}
              onChange={(event) => setInstagramLinks(event.target.value)}
            />
          </div>

          <div className="grid gap-3 md:grid-cols-4">
            <Toggle label="Public reply" checked={publicReply} onChange={setPublicReply} />
            <Toggle label="DM reply" checked={dm} onChange={setDm} />
            <Toggle label="WhatsApp CTA" checked={whatsapp} onChange={setWhatsapp} />
            <Toggle label="AI follow-up" checked={aiFollowup} onChange={setAiFollowup} />
          </div>

          <div className="grid gap-3 rounded-md border border-[var(--border)] bg-[var(--muted)] p-3 md:grid-cols-2">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">Keywords</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {keywordList.map((keyword) => (
                  <Badge key={keyword}>{keyword}</Badge>
                ))}
              </div>
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">Product</div>
              <div className="mt-2 flex flex-wrap gap-2">
                <Badge tone="success">{productName}</Badge>
                <Badge>{platform}</Badge>
              </div>
            </div>
          </div>

          {mutation.error ? (
            <div className="rounded-md border border-[var(--danger)] p-3 text-sm text-[var(--danger)]">
              {mutation.error instanceof Error ? mutation.error.message : "Could not create campaign."}
            </div>
          ) : null}

          <Button type="submit" disabled={mutation.isPending || !name.trim() || keywordList.length === 0}>
            {mutation.isPending ? "Creating..." : "Create active automation"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function Toggle({
  label,
  checked,
  onChange
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="rounded-md border border-[var(--border)] p-3 text-sm">
      <div className="flex items-center gap-2 font-medium">
        <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
        {label}
      </div>
    </label>
  );
}
