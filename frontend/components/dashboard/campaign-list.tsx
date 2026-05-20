"use client";

import { useQuery } from "@tanstack/react-query";
import { Bot, MessageSquareText, Send } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/services/api";

export function CampaignList() {
  const { data = [] } = useQuery({ queryKey: ["campaigns"], queryFn: api.campaigns });

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {data.map((campaign) => (
        <Card key={campaign.id}>
          <CardHeader>
            <div>
              <CardTitle>{campaign.name}</CardTitle>
              <div className="mt-1 text-sm text-[var(--muted-foreground)]">{campaign.product_focus.join(", ")}</div>
            </div>
            <Badge tone={campaign.status === "active" ? "success" : "neutral"}>{campaign.status}</Badge>
          </CardHeader>
          <CardContent>
            <div className="mb-4 flex flex-wrap gap-2">
              {campaign.keyword_triggers.map((keyword) => (
                <Badge key={keyword}>{keyword}</Badge>
              ))}
            </div>
            <div className="grid gap-3 text-sm sm:grid-cols-3">
              <div className="flex items-center gap-2">
                <MessageSquareText size={16} className="text-[var(--primary)]" />
                {campaign.public_reply_enabled ? "Public replies on" : "Public replies off"}
              </div>
              <div className="flex items-center gap-2">
                <Send size={16} className="text-[var(--primary)]" />
                {campaign.dm_enabled ? "DMs on" : "DMs off"}
              </div>
              <div className="flex items-center gap-2">
                <Bot size={16} className="text-[var(--primary)]" />
                {campaign.whatsapp_followup_enabled ? "WhatsApp follow-up" : "No WA follow-up"}
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
