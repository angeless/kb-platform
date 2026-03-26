"use client";

import { useState } from "react";
import { WikiSidebar } from "@/components/wiki-sidebar";
import { useWikiScrollRef } from "@/components/wiki-scroll-context";

interface WikiLayoutProps {
  projectId: string;
  children: React.ReactNode;
}

export function WikiLayout({ projectId, children }: WikiLayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const scrollRef = useWikiScrollRef();

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile hamburger */}
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed left-4 top-[4.5rem] z-30 rounded-lg bg-slate-900 p-2 shadow-lg md:hidden"
        aria-label="打开 Wiki 导航"
      >
        <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Sidebar — desktop */}
      <div className="hidden md:block">
        <WikiSidebar
          projectId={projectId}
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
      </div>

      {/* Sidebar — mobile slide-out */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-200 md:hidden ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <WikiSidebar projectId={projectId} />
        <button
          onClick={() => setMobileOpen(false)}
          className="absolute right-2 top-2 rounded p-1 text-slate-400 hover:text-white md:hidden"
          aria-label="关闭导航"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Main content */}
      <main
        ref={scrollRef as React.RefObject<HTMLElement>}
        className="flex-1 overflow-y-auto bg-white"
      >
        {children}
      </main>
    </div>
  );
}
