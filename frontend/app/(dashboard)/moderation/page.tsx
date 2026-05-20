"use client";

import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, Td, Th } from "@/components/ui/table";
import { api } from "@/services/api";

export default function ModerationPage() {
  const { data = [] } = useQuery({ queryKey: ["moderation"], queryFn: api.moderation });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Moderation</h1>
        <p className="text-sm text-[var(--muted-foreground)]">Safety actions for abuse, spam, medical-risk content, and prompt injection.</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Moderation Logs</CardTitle>
          <Badge tone="warning">{data.length} cases</Badge>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <thead>
                <tr>
                  <Th>Action</Th>
                  <Th>Flags</Th>
                  <Th>Confidence</Th>
                  <Th>Notes</Th>
                </tr>
              </thead>
              <tbody>
                {data.map((item) => (
                  <tr key={String(item.id)}>
                    <Td>{String(item.action)}</Td>
                    <Td>{Array.isArray(item.flags) ? item.flags.join(", ") : ""}</Td>
                    <Td>{Math.round(Number(item.confidence ?? 0) * 100)}%</Td>
                    <Td>{String(item.notes ?? "")}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
            {data.length === 0 ? (
              <p className="mt-4 text-sm text-[var(--muted-foreground)]">No moderation events yet.</p>
            ) : null}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

