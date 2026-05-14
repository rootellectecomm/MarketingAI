import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/dashboard/providers";

export const metadata: Metadata = {
  title: "Rootellect AI Automation",
  description: "Admin dashboard for Rootellect Instagram AI automation."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

