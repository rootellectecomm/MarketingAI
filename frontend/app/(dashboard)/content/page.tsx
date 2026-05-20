"use client";

import { useMutation } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/services/api";

const CONTENT_TYPES = [
  "reel_hook",
  "story_idea",
  "carousel",
  "comment_cta",
  "founder_script",
  "ugc_prompt"
];

export default function ContentPage() {
  const [contentType, setContentType] = useState("reel_hook");
  const [topic, setTopic] = useState("PCOS and stress");
  const [products, setProducts] = useState("Mind Calm, PCOS Support");

  const mutation = useMutation({
    mutationFn: () =>
      api.generateContent({
        content_type: contentType,
        topic,
        product_focus: products.split(",").map((p) => p.trim()).filter(Boolean)
      })
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate();
  }

  const result = mutation.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Content Studio</h1>
        <p className="text-sm text-[var(--muted-foreground)]">Generate premium wellness content for reels, stories, and CTAs.</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Generate</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-3 md:grid-cols-2" onSubmit={onSubmit}>
            <select
              className="h-10 rounded-md border border-[var(--border)] bg-transparent px-3 text-sm"
              value={contentType}
              onChange={(e) => setContentType(e.target.value)}
            >
              {CONTENT_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
            <Input placeholder="Topic" value={topic} onChange={(e) => setTopic(e.target.value)} />
            <Input
              className="md:col-span-2"
              placeholder="Product focus (comma-separated)"
              value={products}
              onChange={(e) => setProducts(e.target.value)}
            />
            <Button type="submit" disabled={mutation.isPending} className="md:col-span-2">
              {mutation.isPending ? "Generating…" : "Generate content"}
            </Button>
          </form>
        </CardContent>
      </Card>
      {result ? (
        <Card>
          <CardHeader>
            <CardTitle>{result.title ?? result.topic}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {result.hooks?.length ? (
              <div>
                <p className="font-medium">Hooks</p>
                <ul className="list-disc pl-5">
                  {result.hooks.map((hook) => (
                    <li key={hook}>{hook}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            {result.body ? <p>{result.body}</p> : null}
            {result.cta ? <p className="text-[var(--muted-foreground)]">CTA: {result.cta}</p> : null}
            {result.raw ? <pre className="overflow-x-auto rounded-md bg-[var(--muted)] p-3 text-xs">{result.raw}</pre> : null}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
