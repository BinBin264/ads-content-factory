import type { ReactNode } from "react";
import { Link } from "react-router-dom";

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-[#f4f6fb]">
      <header className="app-header">
        <div className="site-header-inner flex w-full items-center gap-4 px-4 py-4 sm:px-6 lg:px-8">
          <Link className="brand-link" to="/" aria-label="AI Video Content Factory home">
            <img className="brand-logo" src="/logo.png" alt="AI Video Content Factory" />
            <span className="brand-copy">
              <strong>AI Video</strong>
              <small>Content Factory</small>
            </span>
          </Link>
          <div id="app-header-actions" className="ml-auto min-w-0 flex-1" />
        </div>
      </header>
      <main className="w-full pb-6 pt-0">{children}</main>
    </div>
  );
}
