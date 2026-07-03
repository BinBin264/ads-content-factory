import type { ReactNode } from "react";
import { Link } from "react-router-dom";

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-app-shell">
      <header className="border-b border-white/70 bg-white/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center px-6 py-5">
          <Link className="flex items-center gap-4 transition hover:opacity-85" to="/">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-slate-950 text-sm font-black text-white shadow-soft">
              AF
            </div>
            <div>
              <h1 className="text-xl font-black text-slate-950">AI Ads Video Factory</h1>
              <p className="text-sm text-slate-500">Product intelligence, creative angles, ad scripts, and video exports.</p>
            </div>
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-6">{children}</main>
    </div>
  );
}
