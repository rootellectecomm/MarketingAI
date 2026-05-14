import { CampaignList } from "@/components/dashboard/campaign-list";

export default function CampaignsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Campaigns</h1>
        <p className="text-sm text-[var(--muted-foreground)]">Keyword triggers, product focus, and automated response channels.</p>
      </div>
      <CampaignList />
    </div>
  );
}

