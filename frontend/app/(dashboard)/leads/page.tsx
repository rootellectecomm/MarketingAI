import { LeadsTable } from "@/components/dashboard/leads-table";

export default function LeadsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Leads</h1>
        <p className="text-sm text-[var(--muted-foreground)]">Lead scores, opt-ins, lifecycle stages, and campaign tags.</p>
      </div>
      <LeadsTable />
    </div>
  );
}

