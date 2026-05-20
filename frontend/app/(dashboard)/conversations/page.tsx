"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/services/api";

export default function ConversationsPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { data: conversations = [], isLoading } = useQuery({
    queryKey: ["conversations"],
    queryFn: api.conversations
  });
  const { data: messages = [] } = useQuery({
    queryKey: ["conversation-messages", selectedId],
    queryFn: () => api.conversationMessages(selectedId!),
    enabled: Boolean(selectedId)
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Conversations</h1>
        <p className="text-sm text-[var(--muted-foreground)]">Live inbox across Instagram DMs and WhatsApp.</p>
      </div>
      <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
        <Card>
          <CardHeader>
            <CardTitle>Inbox</CardTitle>
            <Badge>{conversations.length} threads</Badge>
          </CardHeader>
          <CardContent className="space-y-2">
            {isLoading ? <p className="text-sm text-[var(--muted-foreground)]">Loading…</p> : null}
            {!isLoading && conversations.length === 0 ? (
              <p className="text-sm text-[var(--muted-foreground)]">No conversations yet. Connect Meta and receive DMs or WhatsApp messages.</p>
            ) : null}
            {conversations.map((conversation) => (
              <button
                key={conversation.id}
                type="button"
                onClick={() => setSelectedId(conversation.id)}
                className={`w-full rounded-md border p-3 text-left transition ${
                  selectedId === conversation.id ? "border-[var(--primary)] bg-[var(--muted)]" : "border-[var(--border)]"
                }`}
              >
                <div className="text-sm font-medium">@{conversation.username ?? conversation.external_user_id}</div>
                <div className="mt-1 text-xs text-[var(--muted-foreground)]">{conversation.channel}</div>
              </button>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Thread</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {!selectedId ? (
              <p className="text-sm text-[var(--muted-foreground)]">Select a conversation to view messages.</p>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`rounded-md p-3 text-sm ${
                    message.direction === "outbound"
                      ? "ml-8 bg-[var(--primary)] text-[var(--primary-foreground)]"
                      : "mr-8 border border-[var(--border)]"
                  }`}
                >
                  {message.body}
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
