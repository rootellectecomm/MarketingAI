import { ProviderStatusPanel } from "@/components/dashboard/provider-status";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="text-sm text-[var(--muted-foreground)]">Provider readiness, credentials, and automation thresholds.</p>
      </div>
      <ProviderStatusPanel />
      <Card>
        <CardHeader>
          <CardTitle>Automation Controls</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-3">
            <Input defaultValue="0.78" aria-label="Autosend confidence" />
            <Input defaultValue="mock" aria-label="Provider mode" />
            <Button type="button">Update settings</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

