"use client";

import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/services/api";

const providerLabels: Record<string, string> = {
  mock: "Test mode",
  instagram_professional: "Instagram Professional",
  facebook_page_backed: "Facebook Page-backed"
};

export function ProviderStatusPanel() {
  const { data } = useQuery({ queryKey: ["providers"], queryFn: api.providerStatus });
  const providerMode = data?.provider_mode ?? "instagram_professional";
  const facebookPages = data?.facebook_pages ?? [];
  const instagramAccounts = data?.instagram_accounts ?? [];
  const setupWarnings = data?.setup_warnings ?? [];
  const rows = [
    ["Meta OAuth", data?.meta_env_ready],
    ["Facebook", data?.facebook_ready],
    ["Instagram", data?.instagram_ready],
    ["WhatsApp", data?.whatsapp_ready],
    ["OpenAI", data?.openai_ready],
    ["Chroma", Boolean(data?.chroma_collection)]
  ] as const;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Provider Status</CardTitle>
        <Badge tone={providerMode === "mock" ? "warning" : "success"}>
          {providerLabels[providerMode] ?? "Configured"}
        </Badge>
      </CardHeader>
      <CardContent>
        {data?.backend_reachable === false ? (
          <div className="mb-3 rounded-md border border-[var(--danger)] bg-[color-mix(in_srgb,var(--danger)_10%,transparent)] p-3 text-sm text-[var(--danger)]">
            Backend status is not reachable from this frontend deployment.
          </div>
        ) : null}
        {setupWarnings.length ? (
          <div className="mb-3 space-y-2">
            {setupWarnings.map((warning) => (
              <div
                key={warning}
                className="rounded-md border border-[var(--warning)] bg-[color-mix(in_srgb,var(--warning)_12%,transparent)] p-3 text-sm text-[var(--warning)]"
              >
                {warning}
              </div>
            ))}
          </div>
        ) : null}
        <div className="grid gap-3 sm:grid-cols-2">
          {rows.map(([label, ready]) => (
            <div key={label} className="flex items-center justify-between rounded-md border border-[var(--border)] p-3">
              <span className="text-sm">{label}</span>
              <Badge tone={ready ? "success" : "warning"}>{ready ? "Ready" : "Not connected"}</Badge>
            </div>
          ))}
        </div>
        {facebookPages.length || instagramAccounts.length ? (
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {facebookPages.length ? (
              <div className="rounded-md border border-[var(--border)] p-3">
                <div className="text-xs font-semibold uppercase text-[var(--muted-foreground)]">Connected Facebook Pages</div>
                <div className="mt-2 space-y-1">
                  {facebookPages.map((page) => (
                    <div key={page.id ?? page.name} className="text-sm">
                      {page.name}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
            {instagramAccounts.length ? (
              <div className="rounded-md border border-[var(--border)] p-3">
                <div className="text-xs font-semibold uppercase text-[var(--muted-foreground)]">Connected Instagram Accounts</div>
                <div className="mt-2 space-y-1">
                  {instagramAccounts.map((account) => (
                    <div key={account.id} className="text-sm">
                      @{account.username}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
