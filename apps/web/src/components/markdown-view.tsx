"use client";

import ReactMarkdown from "react-markdown";

interface MarkdownViewProps {
  content: string;
  className?: string;
}

export function MarkdownView({ content, className }: MarkdownViewProps) {
  return (
    <div className={`prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-a:text-primary-600 prose-code:rounded prose-code:bg-gray-100 prose-code:px-1 prose-code:text-sm ${className || ""}`}>
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
