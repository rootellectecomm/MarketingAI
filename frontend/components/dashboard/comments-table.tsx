"use client";

import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, Td, Th } from "@/components/ui/table";
import { api } from "@/services/api";

export function CommentsTable() {
  const { data = [] } = useQuery({ queryKey: ["comments"], queryFn: api.comments });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Comment Queue</CardTitle>
        <Badge tone="neutral">{data.length} items</Badge>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <thead>
              <tr>
                <Th>User</Th>
                <Th>Comment</Th>
                <Th>Media</Th>
                <Th>Status</Th>
                <Th>Created</Th>
              </tr>
            </thead>
            <tbody>
              {data.map((comment) => (
                <tr key={comment.id}>
                  <Td>@{comment.username ?? "unknown"}</Td>
                  <Td className="max-w-lg">{comment.text}</Td>
                  <Td>{comment.media_id ?? "n/a"}</Td>
                  <Td>
                    <div className="flex gap-2">
                      <Badge tone={comment.replied ? "success" : "warning"}>{comment.replied ? "Replied" : "Pending"}</Badge>
                      {comment.hidden ? <Badge tone="danger">Hidden</Badge> : null}
                    </div>
                  </Td>
                  <Td>{new Date(comment.created_at).toLocaleString()}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

