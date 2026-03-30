"use client";

import { useEffect, useState } from "react";
import { api, ApiClientError } from "@/lib/api";

interface DiffLine {
  type: "context" | "added" | "removed";
  content: string;
}

interface DiffData {
  from_version: number;
  to_version: number;
  from_change_reason: string | null;
  to_change_reason: string | null;
  diff_lines: DiffLine[];
  stats: { added: number; removed: number; unchanged: number };
}

interface VersionDiffProps {
  docId: string;
  fromVersion: number;
  toVersion: number;
}

const LINE_COLORS: Record<string, string> = {
  added: "bg-green-50 text-green-800",
  removed: "bg-red-50 text-red-800",
  context: "text-gray-700",
};

const LINE_PREFIXES: Record<string, string> = {
  added: "+ ",
  removed: "- ",
  context: "  ",
};

export function VersionDiff({ docId, fromVersion, toVersion }: VersionDiffProps) {
  const [diff, setDiff] = useState<DiffData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchDiff = async () => {
      setLoading(true);
      setError("");
      try {
        const resp = await api.get<DiffData>(
          `/v1/docs/${docId}/diff?from_version=${fromVersion}&to_version=${toVersion}`,
        );
        setDiff(resp.data);
      } catch (e) {
        setError(e instanceof ApiClientError ? e.message : "加载 diff 失败");
      } finally {
        setLoading(false);
      }
    };
    fetchDiff();
  }, [docId, fromVersion, toVersion]);

  if (loading) return <div className="py-6 text-center text-sm text-gray-400">加载中...</div>;
  if (error) return <div className="py-6 text-center text-sm text-red-500">{error}</div>;
  if (!diff) return null;

  return (
    <div>
      <div className="mb-3 flex items-center gap-4 text-xs text-gray-500">
        <span>v{diff.from_version} → v{diff.to_version}</span>
        <span className="text-green-600">+{diff.stats.added}</span>
        <span className="text-red-600">-{diff.stats.removed}</span>
        <span>{diff.stats.unchanged} 行不变</span>
      </div>
      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white font-mono text-xs leading-5">
        {diff.diff_lines.map((line, i) => (
          <div key={i} className={`whitespace-pre-wrap px-3 py-0.5 ${LINE_COLORS[line.type]}`}>
            {LINE_PREFIXES[line.type]}{line.content}
          </div>
        ))}
        {diff.diff_lines.length === 0 && (
          <div className="px-3 py-4 text-center text-gray-400">内容完全相同</div>
        )}
      </div>
    </div>
  );
}
