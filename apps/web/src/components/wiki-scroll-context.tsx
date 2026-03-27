"use client";

import { createContext, useContext, useRef } from "react";

const WikiScrollContext = createContext<React.RefObject<HTMLElement | null>>({ current: null });

export function WikiScrollProvider({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLElement | null>(null);
  return (
    <WikiScrollContext.Provider value={ref}>
      {children}
    </WikiScrollContext.Provider>
  );
}

export function useWikiScrollRef() {
  return useContext(WikiScrollContext);
}
