"use client";

import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/services/api";

export function ProviderStatusPanel() {
  const { data } = useQuery({ queryKey: ["providers"], queryFn: api.providerStatus });
  const rows = [
    ["Instagram", data?.instagram_ready],
    ["WhatsApp", data?.whatsapp_ready],
    ["OpenAI", data?.openai_ready],
    ["Chroma", Boolean(data?.chroma_collection)]
  ] as const;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Provider Status</CardTitle>
        <Badge>{data?.provider_mode ?? "mock"}</Badge>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3 sm:grid-cols-2">
          {rows.map(([label, ready]) => (
            <div key={label} className="flex items-center justify-between rounded-md border border-[var(--border)] p-3">
              <span className="text-sm">{label}</span>
              <Badge tone={ready ? "success" : "warning"}>{ready ? "Ready" : "Mock"}</Badge>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
