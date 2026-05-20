"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { useEffect, useRef } from "react";
import { ProviderStatusPanel } from "@/components/dashboard/provider-status";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { api } from "@/services/api";

export default function SettingsPage() {
  const providerMode = process.env.NEXT_PUBLIC_PROVIDER_MODE ?? "facebook_page_backed";
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
  const queryClient = useQueryClient();
  const { data: providers } = useQuery({ queryKey: ["providers"], queryFn: api.providerStatus });
  const instagramReady = providers?.instagram_ready ?? false;
  const canSync = instagramReady && providers?.provider_mode !== "mock";
  const autoSyncStarted = useRef(false);
  const syncMutation = useMutation({
    mutationFn: () => api.syncMetaComments(),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["metrics"] }),
        queryClient.invalidateQueries({ queryKey: ["comments"] }),
        queryClient.invalidateQueries({ queryKey: ["leads"] }),
        queryClient.invalidateQueries({ queryKey: ["providers"] })
      ]);
    }
  });
  const syncErrorMessage =
    syncMutation.error instanceof Error
      ? syncMutation.error.message
      : "Sync failed before the backend returned a readable error. Redeploy the latest frontend and try again.";

  useEffect(() => {
    if (autoSyncStarted.current || typeof window === "undefined") {
      return;
    }
    const searchParams = new URLSearchParams(window.location.search);
    if (searchParams.get("meta") === "connected") {
      autoSyncStarted.current = true;
      queryClient.invalidateQueries({ queryKey: ["providers"] });
      syncMutation.mutate();
    }
  }, [syncMutation, queryClient]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="text-sm text-[var(--muted-foreground)]">Provider readiness, credentials, and automation thresholds.</p>
      </div>
      <ProviderStatusPanel />
      <Card>
        <CardHeader>
          <CardTitle>Facebook And Instagram</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="text-sm font-medium">Connect Rootellect Meta accounts</div>
              <div className="text-sm text-[var(--muted-foreground)]">
                Authorize the Facebook Page that owns the linked Instagram professional account.
              </div>
            </div>
            <Button
              type="button"
              onClick={async () => {
                const result = await api.metaConnectUrl();
                if (result.url) {
                  window.location.href = result.url;
                  return;
                }
                alert(
                  result.missing_or_placeholder_env?.length
                    ? `Configure backend env: ${result.missing_or_placeholder_env.join(", ")}`
                    : "Meta connect is not ready. Check backend settings."
                );
              }}
            >
              Connect Facebook & Instagram
            </Button>
          </div>
          <div className="mt-4 flex flex-col gap-3 rounded-md border border-[var(--border)] p-3 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="text-sm font-medium">Recent Instagram comments</div>
              <div className="text-sm text-[var(--muted-foreground)]">
                Import the latest comments from the connected Instagram professional account.
              </div>
              {!canSync ? (
                <div className="mt-2 text-sm text-[var(--warning)]">
                  {providers?.provider_mode === "mock"
                    ? "Backend is in mock mode. Set PROVIDER_MODE=facebook_page_backed on the Vercel backend project, redeploy, then connect Meta again."
                    : !providers?.facebook_ready
                      ? "Connect Facebook & Instagram first (see Provider Status above)."
                      : "Facebook is connected but no Instagram professional account was linked. In Meta, link IG Business to your Facebook Page, then reconnect."}
                </div>
              ) : null}
              {syncMutation.data ? (
                <div className="mt-2 text-sm text-[var(--muted-foreground)]">
                  Synced {syncMutation.data.comments_created} new and {syncMutation.data.comments_updated} existing comments from{" "}
                  {syncMutation.data.media_seen} posts.
                </div>
              ) : null}
              {syncMutation.error ? (
                <div className="mt-2 max-w-3xl break-words text-sm text-[var(--danger)]">
                  {syncErrorMessage}
                </div>
              ) : null}
            </div>
            <Button
              type="button"
              variant="secondary"
              disabled={syncMutation.isPending || !canSync}
              onClick={() => syncMutation.mutate()}
            >
              <RefreshCw size={16} />
              {syncMutation.isPending ? "Syncing" : "Sync comments"}
            </Button>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Automation Controls</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-3">
            <Input defaultValue="0.78" aria-label="Autosend confidence" />
            <Input defaultValue={providerMode} aria-label="Provider mode" />
            <Button type="button">Update settings</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
