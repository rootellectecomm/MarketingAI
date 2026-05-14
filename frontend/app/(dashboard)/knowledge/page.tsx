import { FileText, PackageCheck, ShieldCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const documents = [
  { title: "Rootellect Products", icon: PackageCheck, status: "Seeded" },
  { title: "Shipping And Refunds", icon: FileText, status: "Seeded" },
  { title: "Safety Guardrails", icon: ShieldCheck, status: "Active" }
];

export default function KnowledgePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Knowledge Base</h1>
        <p className="text-sm text-[var(--muted-foreground)]">Product, policy, FAQ, and safety context for RAG-backed replies.</p>
      </div>
      <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="grid gap-4">
          {documents.map((doc) => {
            const Icon = doc.icon;
            return (
              <Card key={doc.title}>
                <CardHeader>
                  <CardTitle>{doc.title}</CardTitle>
                  <Icon size={18} className="text-[var(--primary)]" />
                </CardHeader>
                <CardContent>
                  <div className="text-sm text-[var(--muted-foreground)]">{doc.status}</div>
                </CardContent>
              </Card>
            );
          })}
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Add Knowledge</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-3">
              <Input placeholder="Title" />
              <Input placeholder="Category" />
              <Textarea placeholder="Content" />
              <Button type="button">Save entry</Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

