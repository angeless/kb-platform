"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";

interface DiffLine {
  type: string;
  content: string;
}

interface DiffResult {
  doc_id: string;
  from_version: number;
  to_version: number;
  from_change_reason: string | null;
  to_change_reason: string | null;
  diff_lines: DiffLine[];
  stats: { added: number; removed: number; unchanged: number };
}

export default function DocDiffPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const docId = params.id as string;

  const fromVer = parseInt(searchParams.get("from") || "1", 10);
  const toVer = parseInt(searchParams.get("to") || "2", 10);

  const [diff, setDiff] = useState<DiffResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetch = async () => {
      try {
        const resp = await api.get<DiffResult>(
          `/v1/docs/${docId}/diff?from_version=${fromVer}&to_version=${toVer}`,
        );
        setDiff(resp.data);
      } catch (e) {
        setError(e instanceof ApiClientError ? e.message : "加载失败");
      } finally {
        setIsLoading(false);
      }
    };
    fetch();
  }, [docId, fromVer, toVer]);

  if (isLoading) return <div className="py-12 text-center text-gray-400">加载中...</div>;
  if (error) return <div className="py-12 text-center text-red-500">{error}</div>;
  if (!diff) return null;

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-4">
        <Link href={`/docs/${docId}`} className="text-sm text-primary-600 hover:underline">
          ← 返回文档
        </Link>
      </div>

      <h1 className="mb-2 text-2xl font-bold text-gray-900">版本对比</h1>
      <div className="mb-4 flex items-center gap-4 text-sm text-gray-500">
        <span>v{diff.from_version} → v{diff.to_version}</span>
        <span className="text-green-600">+{diff.stats.added} 行</span>
        <span className="text-red-600">-{diff.stats.removed} 行</span>
        <span className="text-gray-400">{diff.stats.unchanged} 行不变</span>
      </div>

      {diff.from_change_reason && (
        <p className="mb-1 text-xs text-gray-400">v{diff.from_version}：{diff.from_change_reason}</p>
      )}
      {diff.to_change_reason && (
        <p className="mb-4 text-xs text-gray-400">v{diff.to_version}：{diff.to_change_reason}</p>
      )}

      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <pre className="p-0 text-sm">
          {diff.diff_lines.map((line, i) => (
            <div
              key={i}
              className={`px-4 py-0.5 font-mono ${
                line.type === "added"
                  ? "bg-green-50 text-green-800"
                  : line.type === "removed"
                    ? "bg-red-50 text-red-800"
                    : "text-gray-600"
              }`}
            >
              <span className="mr-3 inline-block w-4 text-gray-400">
                {line.type === "added" ? "+" : line.type === "removed" ? "-" : " "}
              </span>
              {line.content}
            </div>
          ))}
        </pre>
      </div>
    </div>
  );
}
