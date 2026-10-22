import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Providers } from "@/components/Providers";
import { themeInitScript } from "@/components/ThemeToggle";
import "./globals.css";

const appName = process.env.NEXT_PUBLIC_APP_NAME ?? "SaaS Starter Kit";

export const metadata: Metadata = {
  title: { default: appName, template: `%s · ${appName}` },
  description: "Multi-tenant SaaS starter: organizations, team invites, API keys, plans and billing.",
  icons: { icon: "/icon.svg" },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="min-h-screen">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
