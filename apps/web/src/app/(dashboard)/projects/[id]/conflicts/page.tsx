"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

interface Conflict {
  id: string;
  description: string;
  status: string;
  resolved_at: string | null;
  created_at: string;
}

export default function ConflictsPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [resolveId, setResolveId] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [resolving, setResolving] = useState(false);

  const fetchConflicts = useCallback(async () => {
    setIsLoading(true);
    try {
      const resp = await api.get<Conflict[]>(
        `/v1/conflicts?project_id=${projectId}`,
      );
      setConflicts(resp.data);
      setTotal(resp.meta?.total ?? resp.data.length);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchConflicts();
  }, [fetchConflicts]);

  const handleResolve = async () => {
    if (!resolveId) return;
    setResolving(true);
    try {
      await api.post(`/v1/conflicts/${resolveId}/resolve`, {
        resolution_note: note,
      });
      setResolveId(null);
      setNote("");
      fetchConflicts();
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "解决失败");
    } finally {
      setResolving(false);
    }
  };

  return (
    <div>
      <div className="mb-4">
        <Link href={`/projects/${projectId}`} className="text-sm text-primary-600 hover:underline">
          ← 返回项目
        </Link>
      </div>

      <h1 className="mb-6 text-2xl font-bold text-gray-900">冲突管理</h1>

      {error && <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

      {/* Resolve Modal */}
      {resolveId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h3 className="mb-3 text-lg font-semibold">解决冲突</h3>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="请描述解决方案..."
              rows={4}
              className="mb-4 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => { setResolveId(null); setNote(""); }}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700"
              >
                取消
              </button>
              <button
                onClick={handleResolve}
                disabled={resolving || !note.trim()}
                className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                {resolving ? "提交中..." : "确认解决"}
              </button>
            </div>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="py-12 text-center text-gray-400">加载中...</div>
      ) : conflicts.length === 0 ? (
        <div className="py-12 text-center text-gray-400">暂无冲突记录</div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-gray-500">共 {total} 条冲突</p>
          {conflicts.map((c) => (
            <div
              key={c.id}
              className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={c.status === "open" ? "pending" : c.status === "resolved" ? "completed" : "failed"} />
                    <span className="text-xs text-gray-400">
                      {new Date(c.created_at).toLocaleString("zh-CN")}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-gray-700">{c.description}</p>
                  {c.resolved_at && (
                    <p className="mt-1 text-xs text-gray-400">
                      解决于 {new Date(c.resolved_at).toLocaleString("zh-CN")}
                    </p>
                  )}
                </div>
                {c.status === "open" && (
                  <button
                    onClick={() => setResolveId(c.id)}
                    className="ml-4 rounded-lg border border-primary-300 px-3 py-1.5 text-sm text-primary-600 hover:bg-primary-50"
                  >
                    解决
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
