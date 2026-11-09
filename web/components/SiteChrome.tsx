"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSyncExternalStore } from "react";

import { useDashboard } from "./DashboardProvider";
import { Badge } from "./ui";

const links = [
  { href: "/", label: "Verdict" },
  { href: "/gaps", label: "Gap by group" },
  { href: "/before-after", label: "Before vs after" },
  { href: "/models", label: "Model comparison" },
  { href: "/shortlist", label: "Shortlist ratio" },
  { href: "/accuracy", label: "Accuracy" },
  { href: "/runs", label: "Runs" },
  { href: "/method", label: "Method" },
];

function subscribeTheme(callback: () => void) {
  const observer = new MutationObserver(callback);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
  return () => observer.disconnect();
}

function getThemeSnapshot() {
  return document.documentElement.classList.contains("dark");
}

function getServerThemeSnapshot() {
  return false;
}

const emptySubscribe = () => () => {};

function ThemeToggle() {
  const mounted = useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );
  const dark = useSyncExternalStore(
    subscribeTheme,
    getThemeSnapshot,
    getServerThemeSnapshot,
  );

  function toggle() {
    const next = !dark;
    document.documentElement.classList.toggle("dark", next);
    try {
      window.localStorage.setItem("fairscreen-theme", next ? "dark" : "light");
    } catch {
      // Storage can be unavailable in private modes.
    }
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
      aria-pressed={mounted ? dark : undefined}
      className="rounded-lg border border-line bg-surface px-3 py-2 text-xs font-semibold text-ink transition hover:border-teal/50"
    >
      {mounted && dark ? "Light theme" : "Dark theme"}
    </button>
  );
}

export function SiteHeader() {
  const pathname = usePathname();
  const { data, loading, refreshing, refresh } = useDashboard();

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-canvas/95 backdrop-blur">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-center justify-between gap-3 py-4">
          <div className="flex min-w-0 flex-wrap items-center gap-3">
            <Link href="/" className="font-serif text-2xl font-semibold text-ink">
              FairScreen
            </Link>
            <span className="hidden text-sm text-muted sm:inline">
              Matched-CV bias audit
            </span>
            {data?.run.is_simulated ? <Badge tone="warn">Simulated data</Badge> : null}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {data ? (
              <span className="max-w-[16rem] truncate rounded-lg border border-line bg-surface px-3 py-2 text-xs text-muted">
                {data.run.status} / {data.run.variants.toLocaleString()} CVs /{" "}
                {data.run.scores.toLocaleString()} scores
              </span>
            ) : null}
            <button
              type="button"
              onClick={() => void refresh()}
              disabled={loading || refreshing}
              className="rounded-lg border border-line bg-surface px-3 py-2 text-xs font-semibold text-ink transition hover:border-teal/50 disabled:opacity-60"
            >
              {refreshing ? "Refreshing" : "Refresh"}
            </button>
            <ThemeToggle />
          </div>
        </div>
        <nav aria-label="Primary" className="-mx-1 flex flex-wrap gap-1 pb-3">
          {links.map((link) => {
            const active =
              link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={`rounded-md px-2.5 py-1.5 text-xs font-semibold transition sm:text-sm ${
                  active
                    ? "bg-teal-soft text-teal-strong dark:text-teal"
                    : "text-muted hover:bg-surface-2 hover:text-ink"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="mt-12 border-t border-line bg-surface/60">
      <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 py-6 text-xs leading-5 text-muted sm:px-6 lg:px-8">
        <p>
          FairScreen uses synthetic CVs and matched variants. Results apply to one model,
          prompt and test set. They are not a legal compliance finding and do not generalize
          to real applicants.
        </p>
        <p>
          Built for the DataNova FairScreen brief. No applicant data is used. No automated
          hiring decision is made.
        </p>
      </div>
    </footer>
  );
}
