"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { api } from "@/services/api";

export default function KnowledgePage() {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("");
  const [content, setContent] = useState("");
  const { data: documents = [] } = useQuery({ queryKey: ["knowledge"], queryFn: api.knowledge });

  const createMutation = useMutation({
    mutationFn: () => api.createKnowledge({ title, category, content }),
    onSuccess: async () => {
      setTitle("");
      setCategory("");
      setContent("");
      await queryClient.invalidateQueries({ queryKey: ["knowledge"] });
    }
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    createMutation.mutate();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Knowledge Base</h1>
        <p className="text-sm text-[var(--muted-foreground)]">Product, policy, FAQ, and safety context indexed for RAG replies.</p>
      </div>
      <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="grid gap-4">
          {documents.length === 0 ? (
            <Card>
              <CardContent className="pt-6 text-sm text-[var(--muted-foreground)]">
                No documents yet. Seed files load automatically; add entries below to index into Chroma.
              </CardContent>
            </Card>
          ) : null}
          {documents.map((doc) => (
            <Card key={doc.id}>
              <CardHeader>
                <CardTitle>{doc.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-xs text-[var(--muted-foreground)]">{doc.category}</div>
                <p className="mt-2 line-clamp-3 text-sm">{doc.content}</p>
              </CardContent>
            </Card>
          ))}
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Add Knowledge</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-3" onSubmit={onSubmit}>
              <Input placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} required />
              <Input placeholder="Category" value={category} onChange={(e) => setCategory(e.target.value)} required />
              <Textarea placeholder="Content" value={content} onChange={(e) => setContent(e.target.value)} required />
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Saving…" : "Save entry"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
