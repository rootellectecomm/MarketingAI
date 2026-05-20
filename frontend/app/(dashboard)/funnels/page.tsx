"use client";

import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/services/api";

export default function FunnelsPage() {
  const { data: funnels = [] } = useQuery({ queryKey: ["funnels"], queryFn: api.funnels });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Funnels</h1>
        <p className="text-sm text-[var(--muted-foreground)]">Automated nurture journeys from Instagram to WhatsApp and retention.</p>
      </div>
      {funnels.length === 0 ? (
        <Card>
          <CardContent className="pt-6 text-sm text-[var(--muted-foreground)]">
            Default funnel is created on first load when the worker runs. Ensure Redis worker is active on your VPS.
          </CardContent>
        </Card>
      ) : null}
      <div className="grid gap-4">
        {funnels.map((funnel) => (
          <Card key={funnel.id}>
            <CardHeader>
              <CardTitle>{funnel.name}</CardTitle>
              <Badge tone={funnel.status === "active" ? "success" : "neutral"}>{funnel.status}</Badge>
            </CardHeader>
            <CardContent>
              <p className="mb-4 text-sm text-[var(--muted-foreground)]">{funnel.description}</p>
              <p className="mb-2 text-sm font-medium">{funnel.enrolled_leads} leads enrolled</p>
              <ol className="space-y-2 text-sm">
                {funnel.steps.map((step) => (
                  <li key={step.id} className="rounded-md border border-[var(--border)] p-2">
                    <span className="font-medium">Step {step.step_order + 1}</span> · {step.channel} · +{step.delay_hours}h
                    <p className="mt-1 text-[var(--muted-foreground)]">{step.message_template}</p>
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
