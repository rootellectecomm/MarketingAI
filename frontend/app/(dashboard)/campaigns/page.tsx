import { CampaignCommandCenter } from "@/components/dashboard/campaign-command-center";
import { CampaignForm } from "@/components/dashboard/campaign-form";
import { CampaignList } from "@/components/dashboard/campaign-list";

export default function CampaignsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Campaigns</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Build and monitor the full reel comment automation workflow from trigger word to private DM.
        </p>
      </div>
      <CampaignCommandCenter />
      <CampaignForm />
      <CampaignList />
    </div>
  );
}
