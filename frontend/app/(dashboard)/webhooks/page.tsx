"use client";

import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, Td, Th } from "@/components/ui/table";
import { api } from "@/services/api";

export default function WebhooksPage() {
  const { data = [] } = useQuery({ queryKey: ["webhooks"], queryFn: api.webhooks });
  const rows = data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Webhooks</h1>
        <p className="text-sm text-[var(--muted-foreground)]">Meta delivery, signature checks, retries, and event processing status.</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Delivery Log</CardTitle>
          <Badge>{rows.length} events</Badge>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <thead>
                <tr>
                  <Th>Provider</Th>
                  <Th>Event</Th>
                  <Th>Signature</Th>
                  <Th>Status</Th>
                  <Th>Created</Th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={String(row.id)}>
                    <Td>{String(row.provider)}</Td>
                    <Td>{String(row.event_id)}</Td>
                    <Td><Badge tone={row.signature_valid ? "success" : "danger"}>{row.signature_valid ? "Valid" : "Invalid"}</Badge></Td>
                    <Td>{String(row.status)}</Td>
                    <Td>{new Date(String(row.created_at)).toLocaleString()}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
            {rows.length === 0 ? (
              <p className="mt-4 text-sm text-[var(--muted-foreground)]">No webhook deliveries yet.</p>
            ) : null}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

