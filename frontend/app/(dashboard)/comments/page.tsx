import { CommentsTable } from "@/components/dashboard/comments-table";

export default function CommentsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Comments</h1>
        <p className="text-sm text-[var(--muted-foreground)]">Realtime comment intake, reply state, and moderation state.</p>
      </div>
      <CommentsTable />
    </div>
  );
}

