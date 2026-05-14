"use client";

import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, Td, Th } from "@/components/ui/table";
import { api } from "@/services/api";

export function LeadsTable() {
  const { data = [] } = useQuery({ queryKey: ["leads"], queryFn: api.leads });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Lead Pipeline</CardTitle>
        <Badge tone="success">{data.filter((lead) => lead.score >= 75).length} hot</Badge>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <thead>
              <tr>
                <Th>User</Th>
                <Th>Stage</Th>
                <Th>Score</Th>
                <Th>WhatsApp</Th>
                <Th>Tags</Th>
              </tr>
            </thead>
            <tbody>
              {data.map((lead) => (
                <tr key={lead.id}>
                  <Td>@{lead.username ?? lead.external_user_id}</Td>
                  <Td>{lead.lifecycle_stage}</Td>
                  <Td>
                    <Badge tone={lead.score >= 75 ? "success" : lead.score >= 45 ? "warning" : "neutral"}>{lead.score}</Badge>
                  </Td>
                  <Td>{lead.whatsapp_opt_in ? "Opted in" : "No opt-in"}</Td>
                  <Td>{lead.tags.join(", ")}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

