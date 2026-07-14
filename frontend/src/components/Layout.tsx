import type { ReactNode } from "react";
import { Link } from "react-router-dom";

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-app-shell">
      <header className="border-b border-slate-200 bg-white/90 text-slate-950 shadow-soft backdrop-blur">
        <div className="flex w-full items-center gap-4 px-4 py-4 sm:px-6 lg:px-8">
          <Link className="flex items-center gap-4 transition hover:opacity-85" to="/">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-slate-950 text-sm font-black text-white shadow-soft">
              AF
            </div>
            <div>
              <h1 className="text-xl font-black text-slate-950">AI Ads Video Factory</h1>
              <p className="text-sm text-slate-500">Production workspace</p>
            </div>
          </Link>
          <div id="app-header-actions" className="ml-auto min-w-0 flex-1" />
        </div>
      </header>
      <main className="w-full pb-6 pt-0">{children}</main>
    </div>
  );
}
