"use client";

import {
  Activity,
  Bot,
  Brain,
  ChartNoAxesCombined,
  ChevronLeft,
  Gauge,
  Inbox,
  Megaphone,
  MessageSquareText,
  Moon,
  ScrollText,
  Settings,
  ShieldAlert,
  Sun,
  UsersRound,
  Webhook
} from "lucide-react";
import { useTheme } from "next-themes";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/", label: "Overview", icon: Gauge },
  { href: "/analytics", label: "Analytics", icon: ChartNoAxesCombined },
  { href: "/comments", label: "Comments", icon: MessageSquareText },
  { href: "/conversations", label: "Conversations", icon: Inbox },
  { href: "/leads", label: "Leads", icon: UsersRound },
  { href: "/campaigns", label: "Campaigns", icon: Megaphone },
  { href: "/funnels", label: "Funnels", icon: ScrollText },
  { href: "/content", label: "Content", icon: Bot },
  { href: "/moderation", label: "Moderation", icon: ShieldAlert },
  { href: "/knowledge", label: "Knowledge", icon: Brain },
  { href: "/webhooks", label: "Webhooks", icon: Webhook },
  { href: "/settings", label: "Settings", icon: Settings }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { resolvedTheme, setTheme } = useTheme();

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <aside className="fixed inset-y-0 left-0 hidden w-72 border-r border-[var(--border)] bg-[var(--card)] lg:block">
        <div className="flex h-16 items-center gap-3 border-b border-[var(--border)] px-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-[var(--primary)] text-[var(--primary-foreground)]">
            <Bot size={19} />
          </div>
          <div>
            <div className="text-sm font-semibold">Rootellect AI</div>
            <div className="text-xs text-[var(--muted-foreground)]">Automation Console</div>
          </div>
        </div>
        <nav className="space-y-1 p-3">
          {nav.map((item) => {
            const active = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex h-10 items-center gap-3 rounded-md px-3 text-sm transition",
                  active
                    ? "bg-[var(--primary)] text-[var(--primary-foreground)]"
                    : "text-[var(--muted-foreground)] hover:bg-[var(--muted)] hover:text-[var(--foreground)]"
                )}
              >
                <Icon size={18} />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-[var(--border)] bg-[var(--background)]/95 px-4 backdrop-blur md:px-8">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Back">
              <ChevronLeft size={18} />
            </Button>
            <div>
              <div className="text-sm font-semibold">Live Operations</div>
              <div className="text-xs text-[var(--muted-foreground)]">Meta webhook forwarding and AI automation controls</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="icon"
              aria-label="Toggle theme"
              onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
            >
              {resolvedTheme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
            </Button>
            <Button variant="secondary" size="icon" aria-label="Audit log">
              <ScrollText size={17} />
            </Button>
            <Button size="icon" aria-label="Activity">
              <Activity size={17} />
            </Button>
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl px-4 py-6 md:px-8">{children}</main>
      </div>
    </div>
  );
}
