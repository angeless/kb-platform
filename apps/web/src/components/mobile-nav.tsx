"use client";

import { useState } from "react";

interface MobileNavProps {
  children: React.ReactNode;
}

/**
 * Mobile navigation wrapper — shows hamburger menu on small screens,
 * opens sidebar as overlay when clicked.
 */
export function MobileNav({ children }: MobileNavProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Hamburger button — visible only on mobile */}
      <button
        onClick={() => setOpen(true)}
        className="fixed left-4 top-4 z-40 rounded-lg bg-white p-2 shadow-md md:hidden"
        aria-label="打开导航菜单"
      >
        <svg className="h-5 w-5 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          onClick={() => setOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar container — slides in on mobile */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-200 md:relative md:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Close button on mobile */}
        <button
          onClick={() => setOpen(false)}
          className="absolute right-2 top-2 rounded p-1 text-gray-400 hover:text-gray-600 md:hidden"
          aria-label="关闭导航菜单"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        {children}
      </div>
    </>
  );
}
