import { ProviderStatusPanel } from "@/components/dashboard/provider-status";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function SettingsPage() {
  const providerMode = process.env.NEXT_PUBLIC_PROVIDER_MODE ?? "facebook_page_backed";
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
  const metaConnectUrl = `${apiBaseUrl.replace(/\/$/, "")}/meta/connect`;

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
            <a
              href={metaConnectUrl}
              className="inline-flex h-10 items-center justify-center rounded-md bg-[var(--primary)] px-4 text-sm font-medium text-[var(--primary-foreground)] transition hover:opacity-90"
            >
              Connect Facebook & Instagram
            </a>
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
