"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

interface Doc {
  id: string;
  title: string;
  doc_type: string;
  status: string;
  current_version: number;
}

export default function PendingDocsPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [docs, setDocs] = useState<Doc[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchPending = useCallback(async () => {
    setIsLoading(true);
    try {
      const resp = await api.get<Doc[]>(`/v1/docs/pending?project_id=${projectId}`);
      setDocs(resp.data);
      setTotal(resp.meta?.total ?? 0);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => { fetchPending(); }, [fetchPending]);

  return (
    <div>
      <div className="mb-4">
        <Link href={`/projects/${projectId}/docs`} className="text-sm text-primary-600 hover:underline">
          ← 返回文档列表
        </Link>
      </div>

      <h1 className="mb-2 text-2xl font-bold text-gray-900">待分配文档池</h1>
      <p className="mb-6 text-sm text-gray-500">
        以下 {total} 篇文档尚未分配到知识架构节点，需要人工指定归属位置。
      </p>

      {error && <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

      {isLoading ? (
        <div className="py-12 text-center text-gray-400">加载中...</div>
      ) : docs.length === 0 ? (
        <div className="py-12 text-center text-green-600">所有文档已分配完毕!</div>
      ) : (
        <div className="space-y-2">
          {docs.map((doc) => (
            <Link
              key={doc.id}
              href={`/docs/${doc.id}`}
              className="flex items-center justify-between rounded-xl border border-orange-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md"
            >
              <div>
                <h3 className="font-medium text-gray-900">{doc.title}</h3>
                <span className="text-xs text-gray-400">{doc.doc_type} · v{doc.current_version}</span>
              </div>
              <StatusBadge status={doc.status} />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
