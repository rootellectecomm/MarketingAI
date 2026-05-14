import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const rows = [
  ["@wellnesswithriya", "Mind Calm details shared", "Open", "Instagram DM"],
  ["@fitmomsclub", "PCOS Support price requested", "Hot", "Instagram private reply"],
  ["@anikahealth", "Menopause support inquiry", "Escalated", "Instagram DM"]
];

export default function ConversationsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Conversations</h1>
        <p className="text-sm text-[var(--muted-foreground)]">Inbox monitoring across Instagram and WhatsApp.</p>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        {rows.map(([user, message, status, channel]) => (
          <Card key={user}>
            <CardHeader>
              <CardTitle>{user}</CardTitle>
              <Badge tone={status === "Escalated" ? "warning" : status === "Hot" ? "success" : "neutral"}>{status}</Badge>
            </CardHeader>
            <CardContent>
              <div className="text-sm">{message}</div>
              <div className="mt-3 text-xs text-[var(--muted-foreground)]">{channel}</div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

