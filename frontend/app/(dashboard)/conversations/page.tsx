"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/services/api";
import type { ConversationItem } from "@/types/api";

const REASON_LABELS: Record<string, string> = {
  asked_for_person: "Asked for a person",
  catalog_cart: "Sent a cart",
  bot_could_not_answer: "Bot could not answer",
  medical_question: "Health question",
  paused_by_team: "Paused by team",
  team_started: "Team replied"
};

function needsTeam(conversation: ConversationItem) {
  return Boolean(conversation.live_agent?.active);
}

function formatTime(value: string | null | undefined) {
  if (!value) return "";
  return new Date(value).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

export default function ConversationsPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: conversations = [], isLoading } = useQuery({
    queryKey: ["conversations"],
    queryFn: api.conversations,
    refetchInterval: 15000
  });
  const { data: messages = [] } = useQuery({
    queryKey: ["conversation-messages", selectedId],
    queryFn: () => api.conversationMessages(selectedId!),
    enabled: Boolean(selectedId),
    refetchInterval: selectedId ? 10000 : false
  });

  const selected = conversations.find((item) => item.id === selectedId) ?? null;
  const isWhatsApp = selected?.channel === "whatsapp_message";
  const sorted = [...conversations].sort((a, b) => Number(needsTeam(b)) - Number(needsTeam(a)));
  const waitingCount = conversations.filter(needsTeam).length;

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["conversations"] });
    await queryClient.invalidateQueries({ queryKey: ["conversation-messages", selectedId] });
  };

  const reply = useMutation({
    mutationFn: (text: string) => api.replyToConversation(selectedId!, text),
    onSuccess: async () => {
      setDraft("");
      setError(null);
      await refresh();
    },
    onError: (err: Error) => setError(err.message)
  });

  const handover = useMutation({
    mutationFn: (active: boolean) => api.setConversationHandover(selectedId!, active),
    onSuccess: async () => {
      setError(null);
      await refresh();
    },
    onError: (err: Error) => setError(err.message)
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Conversations</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Live inbox across Instagram DMs and WhatsApp. Chats marked “Needs team” are waiting for a person — the bot is
          paused for them.
        </p>
      </div>
      <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
        <Card>
          <CardHeader>
            <CardTitle>Inbox</CardTitle>
            <div className="flex gap-2">
              {waitingCount > 0 ? <Badge>{waitingCount} need team</Badge> : null}
              <Badge>{conversations.length} threads</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {isLoading ? <p className="text-sm text-[var(--muted-foreground)]">Loading…</p> : null}
            {!isLoading && conversations.length === 0 ? (
              <p className="text-sm text-[var(--muted-foreground)]">No conversations yet. Connect Meta and receive DMs or WhatsApp messages.</p>
            ) : null}
            {sorted.map((conversation) => (
              <button
                key={conversation.id}
                type="button"
                onClick={() => {
                  setSelectedId(conversation.id);
                  setError(null);
                }}
                className={`w-full rounded-md border p-3 text-left transition ${
                  selectedId === conversation.id ? "border-[var(--primary)] bg-[var(--muted)]" : "border-[var(--border)]"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm font-medium">
                    {conversation.customer_name ? `${conversation.customer_name} · ` : ""}
                    {conversation.channel === "whatsapp_message" ? "+" : "@"}
                    {conversation.username ?? conversation.external_user_id}
                  </div>
                  {needsTeam(conversation) ? <Badge>Needs team</Badge> : null}
                </div>
                <div className="mt-1 text-xs text-[var(--muted-foreground)]">
                  {conversation.channel === "whatsapp_message" ? "WhatsApp" : conversation.channel}
                  {conversation.live_agent?.active && conversation.live_agent.reason
                    ? ` · ${REASON_LABELS[conversation.live_agent.reason] ?? conversation.live_agent.reason}`
                    : ""}
                  {conversation.last_message_at ? ` · ${formatTime(conversation.last_message_at)}` : ""}
                </div>
              </button>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Thread</CardTitle>
            {selected && isWhatsApp ? (
              <div className="flex items-center gap-2">
                <Badge>{selected.live_agent?.active ? "Team is handling" : "Bot is answering"}</Badge>
                {selected.live_agent?.active ? (
                  <Button size="sm" variant="secondary" disabled={handover.isPending} onClick={() => handover.mutate(false)}>
                    Resume bot
                  </Button>
                ) : (
                  <Button size="sm" variant="secondary" disabled={handover.isPending} onClick={() => handover.mutate(true)}>
                    Take over chat
                  </Button>
                )}
              </div>
            ) : null}
          </CardHeader>
          <CardContent className="space-y-3">
            {!selectedId ? (
              <p className="text-sm text-[var(--muted-foreground)]">Select a conversation to view messages.</p>
            ) : (
              <>
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`rounded-md p-3 text-sm ${
                      message.direction === "outbound"
                        ? "ml-8 bg-[var(--primary)] text-[var(--primary-foreground)]"
                        : "mr-8 border border-[var(--border)]"
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{message.body}</div>
                    <div className="mt-1 text-[10px] opacity-70">
                      {message.direction === "outbound" ? (message.sent_by ? `${message.sent_by} · ` : "Bot · ") : ""}
                      {formatTime(message.created_at)}
                    </div>
                  </div>
                ))}
                {isWhatsApp ? (
                  <form
                    className="space-y-2 border-t border-[var(--border)] pt-3"
                    onSubmit={(event) => {
                      event.preventDefault();
                      if (draft.trim()) reply.mutate(draft.trim());
                    }}
                  >
                    {selected?.reply_window_open === false ? (
                      <p className="text-xs text-[var(--muted-foreground)]">
                        WhatsApp only allows replies within 24 hours of the customer’s last message. This chat’s window
                        has closed — the customer needs to message again first.
                      </p>
                    ) : selected?.reply_window_closes_at ? (
                      <p className="text-xs text-[var(--muted-foreground)]">
                        You can reply until {formatTime(selected.reply_window_closes_at)}. Sending a reply pauses the bot
                        for this customer.
                      </p>
                    ) : null}
                    <Textarea
                      value={draft}
                      onChange={(event) => setDraft(event.target.value)}
                      placeholder="Type your reply to the customer…"
                      className="min-h-20"
                      disabled={selected?.reply_window_open === false}
                    />
                    {error ? <p className="text-xs text-[var(--danger)]">{error}</p> : null}
                    <div className="flex justify-end">
                      <Button type="submit" disabled={!draft.trim() || reply.isPending || selected?.reply_window_open === false}>
                        {reply.isPending ? "Sending…" : "Send reply"}
                      </Button>
                    </div>
                  </form>
                ) : null}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
