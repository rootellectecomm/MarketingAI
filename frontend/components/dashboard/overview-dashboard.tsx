"use client";

import { Activity, Bot, ShieldAlert, TrendingUp, UsersRound } from "lucide-react";
import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricCard } from "@/components/dashboard/metric-card";
import { api } from "@/services/api";
import { percent } from "@/lib/utils";

const SentimentChart = dynamic(
  () => import("@/components/dashboard/sentiment-chart").then((module) => module.SentimentChart),
  {
    ssr: false,
    loading: () => <div className="h-72 rounded-md bg-[var(--muted)]" />
  }
);

export function OverviewDashboard() {
  const { data } = useQuery({ queryKey: ["metrics"], queryFn: api.metrics });
  const metrics = data;
  const sentimentRows = Object.entries(metrics?.sentiment ?? {}).map(([name, value]) => ({ name, value }));

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Overview</h1>
          <p className="text-sm text-[var(--muted-foreground)]">Instagram automation, leads, AI decisions, and safety signals.</p>
        </div>
        <Badge tone="success">Autonomous mode</Badge>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Comments" value={metrics?.comments ?? 0} detail="Normalized and processed" icon={Activity} />
        <MetricCard label="Leads" value={metrics?.leads ?? 0} detail="Internal CRM records" icon={UsersRound} />
        <MetricCard label="Actions" value={metrics?.automated_actions ?? 0} detail="Replies, DMs, hides" icon={Bot} />
        <MetricCard label="Escalations" value={metrics?.escalations ?? 0} detail="Safety-gated cases" icon={ShieldAlert} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.3fr_0.7fr]">
        <Card>
          <CardHeader>
            <CardTitle>Sentiment Trend</CardTitle>
            <TrendingUp className="text-[var(--primary)]" size={18} />
          </CardHeader>
          <CardContent>
            <SentimentChart data={sentimentRows} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>AI Confidence</CardTitle>
            <Badge tone={(metrics?.avg_ai_confidence ?? 0) > 0.78 ? "success" : "warning"}>
              {percent(metrics?.avg_ai_confidence ?? 0)}
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {(metrics?.latest_activity ?? []).map((item) => (
                <div key={String(item.id)} className="flex items-center justify-between border-b border-[var(--border)] pb-3 text-sm last:border-0">
                  <span className="text-[var(--muted-foreground)]">{String(item.id)}</span>
                  <Badge tone={item.blocked ? "warning" : "success"}>{item.blocked ? "Held" : "Sent"}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
