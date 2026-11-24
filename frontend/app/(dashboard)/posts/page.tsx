import { InstagramPostAutomation } from "@/components/dashboard/instagram-post-automation";

export default function PostsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Instagram Posts</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Choose which posts get automatic comment replies and DMs. Comments on every other post are saved to your inbox
          but nobody gets an automatic reply.
        </p>
      </div>
      <InstagramPostAutomation />
    </div>
  );
}
