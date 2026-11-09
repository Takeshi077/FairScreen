import type { Metadata } from "next";
import type { ReactNode } from "react";

import { DashboardProvider } from "@/components/DashboardProvider";
import { SiteFooter, SiteHeader } from "@/components/SiteChrome";

import "./globals.css";

export const metadata: Metadata = {
  title: "FairScreen | Matched-CV bias audit",
  description:
    "Audit LLM CV screeners with matched synthetic pairs. See the gap, test the fix, and check ranking quality.",
};

const themeScript = `
(function () {
  try {
    var stored = localStorage.getItem("fairscreen-theme");
    var dark = stored ? stored === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.classList.toggle("dark", dark);
  } catch (error) {}
})();
`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <DashboardProvider>
          <div className="flex min-h-screen flex-col">
            <SiteHeader />
            <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-7 sm:px-6 sm:py-9 lg:px-8">
              {children}
            </main>
            <SiteFooter />
          </div>
        </DashboardProvider>
      </body>
    </html>
  );
}
