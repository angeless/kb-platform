"use client";

import { useEffect, useState } from "react";

interface TocItem {
  id: string;
  text: string;
  level: number;
}

interface WikiTocProps {
  contentRef: React.RefObject<HTMLDivElement | null>;
  scrollContainerRef?: React.RefObject<HTMLElement | null>;
}

export function WikiToc({ contentRef, scrollContainerRef }: WikiTocProps) {
  const [items, setItems] = useState<TocItem[]>([]);
  const [activeId, setActiveId] = useState("");

  // Extract headings from rendered content
  useEffect(() => {
    const el = contentRef.current;
    if (!el) return;

    const observer = new MutationObserver(() => {
      const headings = el.querySelectorAll("h2, h3");
      const tocItems: TocItem[] = [];
      headings.forEach((h, i) => {
        const id = h.id || `toc-${i}`;
        if (!h.id) h.id = id;
        tocItems.push({
          id,
          text: h.textContent || "",
          level: h.tagName === "H2" ? 2 : 3,
        });
      });
      setItems(tocItems);
    });

    observer.observe(el, { childList: true, subtree: true });

    // Initial extraction
    const headings = el.querySelectorAll("h2, h3");
    const tocItems: TocItem[] = [];
    headings.forEach((h, i) => {
      const id = h.id || `toc-${i}`;
      if (!h.id) h.id = id;
      tocItems.push({
        id,
        text: h.textContent || "",
        level: h.tagName === "H2" ? 2 : 3,
      });
    });
    setItems(tocItems);

    return () => observer.disconnect();
  }, [contentRef]);

  // Track active heading on scroll
  useEffect(() => {
    if (items.length === 0) return;

    const scrollTarget = scrollContainerRef?.current || window;

    const handleScroll = () => {
      const offsetTop = scrollContainerRef?.current
        ? scrollContainerRef.current.getBoundingClientRect().top
        : 0;
      for (let i = items.length - 1; i >= 0; i--) {
        const el = document.getElementById(items[i].id);
        if (el && el.getBoundingClientRect().top - offsetTop <= 100) {
          setActiveId(items[i].id);
          return;
        }
      }
      setActiveId(items[0]?.id || "");
    };

    scrollTarget.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => scrollTarget.removeEventListener("scroll", handleScroll);
  }, [items, scrollContainerRef]);

  if (items.length === 0) return null;

  return (
    <div>
      <h3 className="mb-3 text-xs font-semibold uppercase text-gray-400">目录</h3>
      <ul className="space-y-1">
        {items.map((item) => (
          <li key={item.id}>
            <a
              href={`#${item.id}`}
              onClick={(e) => {
                e.preventDefault();
                const target = document.getElementById(item.id);
                if (target) {
                  if (scrollContainerRef?.current) {
                    const container = scrollContainerRef.current;
                    const top = target.offsetTop - container.offsetTop;
                    container.scrollTo({ top, behavior: "smooth" });
                  } else {
                    target.scrollIntoView({ behavior: "smooth" });
                  }
                }
              }}
              className={`block truncate text-xs transition-colors ${
                item.level === 3 ? "pl-3" : ""
              } ${
                activeId === item.id
                  ? "font-medium text-primary-600"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {item.text}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
