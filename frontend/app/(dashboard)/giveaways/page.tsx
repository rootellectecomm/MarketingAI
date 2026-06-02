import { GiveawayCommandCenter } from "@/components/dashboard/giveaway-command-center";
import { GiveawayForm } from "@/components/dashboard/giveaway-form";
import { GiveawayList } from "@/components/dashboard/giveaway-list";
import { GiveawayParticipantsTable } from "@/components/dashboard/giveaway-participants-table";

export default function GiveawaysPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Giveaway Automations</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Instagram comment-to-DM giveaway workflows with follow-confirmation and reward delivery.
        </p>
      </div>
      <GiveawayCommandCenter />
      <GiveawayForm />
      <GiveawayList />
      <GiveawayParticipantsTable />
    </div>
  );
}
