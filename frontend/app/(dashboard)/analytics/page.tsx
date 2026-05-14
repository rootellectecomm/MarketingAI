"use client";

import { Activity, Bot, TrendingUp, UsersRound } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { MetricCard } from "@/components/dashboard/metric-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/services/api";

export default function AnalyticsPage() {
  const { data } = useQuery({ queryKey: ["metrics"], queryFn: api.metrics });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Analytics</h1>
        <p className="text-sm text-[var(--muted-foreground)]">Conversion, confidence, volume, and automation quality.</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Comment Volume" value={data?.comments ?? 0} detail="All inbound comments" icon={Activity} />
        <MetricCard label="Lead Capture" value={data?.leads ?? 0} detail="CRM-qualified profiles" icon={UsersRound} />
        <MetricCard label="Automation Rate" value={data ? `${Math.round((data.automated_actions / Math.max(data.comments, 1)) * 100)}%` : "0%"} detail="Sent actions per comment" icon={Bot} />
        <MetricCard label="Confidence" value={data ? `${Math.round(data.avg_ai_confidence * 100)}%` : "0%"} detail="Average AI decision score" icon={TrendingUp} />
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Top Performing Reels</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-3">
            {["Mind Calm launch", "PCOS education", "D3 Calcium reel"].map((name, index) => (
              <div key={name} className="rounded-md border border-[var(--border)] p-4">
                <div className="text-sm font-medium">{name}</div>
                <div className="mt-2 text-2xl font-semibold">{[42, 31, 24][index]}%</div>
                <div className="text-sm text-[var(--muted-foreground)]">Lead conversion</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

