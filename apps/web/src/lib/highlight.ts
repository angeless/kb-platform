/**
 * Safe HTML highlight renderer.
 *
 * Only parses <mark>...</mark> tags from PostgreSQL ts_headline output.
 * All other HTML is rendered as plain text, preventing XSS attacks.
 */

import { createElement, type ReactNode } from "react";

/**
 * Render a snippet string that may contain <mark>...</mark> tags
 * into safe React nodes. Any HTML other than <mark> is escaped.
 */
export function renderHighlight(snippet: string): ReactNode[] {
  if (!snippet) return [];

  const parts: ReactNode[] = [];
  let remaining = snippet;
  let key = 0;

  while (remaining.length > 0) {
    const markStart = remaining.indexOf("<mark>");
    if (markStart === -1) {
      // No more <mark> tags — rest is plain text
      parts.push(remaining);
      break;
    }

    // Add text before <mark> as plain text
    if (markStart > 0) {
      parts.push(remaining.slice(0, markStart));
    }

    // Find closing </mark>
    const contentStart = markStart + 6; // length of "<mark>"
    const markEnd = remaining.indexOf("</mark>", contentStart);
    if (markEnd === -1) {
      // Unclosed <mark> — treat rest as plain text
      parts.push(remaining.slice(markStart));
      break;
    }

    // Render the marked content safely
    const markedText = remaining.slice(contentStart, markEnd);
    parts.push(
      createElement(
        "mark",
        { key: key++, className: "rounded-sm bg-yellow-200 px-0.5" },
        markedText,
      ),
    );

    remaining = remaining.slice(markEnd + 7); // length of "</mark>"
  }

  return parts;
}
