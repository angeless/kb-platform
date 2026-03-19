"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";
import { RejectModal } from "@/components/reject-modal";

interface Doc {
  id: string;
  title: string;
  doc_type: string;
  status: string;
  current_version: number;
}

interface BatchResult {
  succeeded: string[];
  failed: { id: string; reason: string }[];
}

export default function ReviewQueuePage() {
  const params = useParams();
  const projectId = params.id as string;

  const [docs, setDocs] = useState<Doc[]>([]);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [showReject, setShowReject] = useState(false);
  const [tab, setTab] = useState<"reviewing" | "draft">("reviewing");

  const fetchDocs = useCallback(async () => {
    setIsLoading(true);
    setSelected(new Set());
    try {
      // Use the docs list with status filter via query
      const endpoint = tab === "reviewing"
        ? `/v1/docs?project_id=${projectId}&page_size=50`
        : `/v1/docs?project_id=${projectId}&page_size=50`;
      const resp = await api.get<Doc[]>(endpoint);
      // Filter client-side by status
      const filtered = resp.data.filter((d) => d.status === tab);
      setDocs(filtered);
      setTotal(filtered.length);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }, [projectId, tab]);

  useEffect(() => { fetchDocs(); }, [fetchDocs]);

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === docs.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(docs.map((d) => d.id)));
    }
  };

  const handleBatchAction = async (action: "review" | "publish" | "reject") => {
    if (selected.size === 0) return;
    setMessage("");
    try {
      const resp = await api.post<BatchResult>(`/v1/docs/batch/${action}`, {
        doc_ids: Array.from(selected),
      });
      const r = resp.data;
      const msg = `成功 ${r.succeeded.length} 篇${r.failed.length > 0 ? `，失败 ${r.failed.length} 篇` : ""}`;
      setMessage(msg);
      setSelected(new Set());
      await fetchDocs();
    } catch (e) {
      setMessage(e instanceof ApiClientError ? e.message : "操作失败");
    }
  };

  const handleReject = async (reason: string) => {
    setShowReject(false);
    // Batch reject doesn't send reason per doc, so we do individual rejects
    setMessage("");
    let ok = 0, fail = 0;
    for (const docId of selected) {
      try {
        await api.post(`/v1/docs/${docId}/reject`, { reject_reason: reason });
        ok++;
      } catch {
        fail++;
      }
    }
    setMessage(`驳回成功 ${ok} 篇${fail > 0 ? `，失败 ${fail} 篇` : ""}`);
    setSelected(new Set());
    await fetchDocs();
  };

  return (
    <div>
      <div className="mb-4">
        <Link href={`/projects/${projectId}`} className="text-sm text-primary-600 hover:underline">
          ← 返回项目
        </Link>
      </div>

      <h1 className="mb-6 text-2xl font-bold text-gray-900">审核管理</h1>

      {/* Tabs */}
      <div className="mb-4 flex gap-1 border-b border-gray-200">
        <button
          onClick={() => setTab("reviewing")}
          className={`border-b-2 px-4 py-2 text-sm ${tab === "reviewing" ? "border-primary-600 font-medium text-primary-600" : "border-transparent text-gray-500"}`}
        >
          待审核
        </button>
        <button
          onClick={() => setTab("draft")}
          className={`border-b-2 px-4 py-2 text-sm ${tab === "draft" ? "border-primary-600 font-medium text-primary-600" : "border-transparent text-gray-500"}`}
        >
          草稿（可批量提交审核）
        </button>
      </div>

      {error && <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}
      {message && <div className="mb-4 rounded-lg bg-blue-50 p-3 text-sm text-blue-600">{message}</div>}

      {/* Batch Actions */}
      {selected.size > 0 && (
        <div className="mb-4 flex items-center gap-3 rounded-lg bg-primary-50 px-4 py-3">
          <span className="text-sm font-medium text-primary-700">已选 {selected.size} 篇</span>
          {tab === "draft" && (
            <button
              onClick={() => handleBatchAction("review")}
              className="rounded bg-primary-600 px-3 py-1 text-xs font-medium text-white hover:bg-primary-700"
            >
              批量提交审核
            </button>
          )}
          {tab === "reviewing" && (
            <>
              <button
                onClick={() => handleBatchAction("publish")}
                className="rounded bg-green-600 px-3 py-1 text-xs font-medium text-white hover:bg-green-700"
              >
                批量通过
              </button>
              <button
                onClick={() => setShowReject(true)}
                className="rounded bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700"
              >
                批量驳回
              </button>
            </>
          )}
          <button
            onClick={() => setSelected(new Set())}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            取消选择
          </button>
        </div>
      )}

      {/* List */}
      {isLoading ? (
        <div className="py-12 text-center text-gray-400">加载中...</div>
      ) : docs.length === 0 ? (
        <div className="py-12 text-center text-gray-400">
          {tab === "reviewing" ? "没有待审核的文档" : "没有草稿文档"}
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="border-b border-gray-200 bg-gray-50">
              <tr>
                <th className="px-3 py-3">
                  <input
                    type="checkbox"
                    checked={selected.size === docs.length && docs.length > 0}
                    onChange={toggleAll}
                    className="rounded border-gray-300"
                  />
                </th>
                <th className="px-5 py-3 text-left font-medium text-gray-600">标题</th>
                <th className="px-5 py-3 text-left font-medium text-gray-600">类型</th>
                <th className="px-5 py-3 text-left font-medium text-gray-600">版本</th>
                <th className="px-5 py-3 text-left font-medium text-gray-600">状态</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((doc) => (
                <tr key={doc.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                  <td className="px-3 py-3 text-center">
                    <input
                      type="checkbox"
                      checked={selected.has(doc.id)}
                      onChange={() => toggleSelect(doc.id)}
                      className="rounded border-gray-300"
                    />
                  </td>
                  <td className="px-5 py-3">
                    <Link href={`/docs/${doc.id}`} className="font-medium text-primary-600 hover:underline">
                      {doc.title}
                    </Link>
                  </td>
                  <td className="px-5 py-3 text-gray-500">{doc.doc_type}</td>
                  <td className="px-5 py-3 text-gray-500">v{doc.current_version}</td>
                  <td className="px-5 py-3"><StatusBadge status={doc.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Reject Modal */}
      {showReject && (
        <RejectModal
          title={`驳回 ${selected.size} 篇文档`}
          onConfirm={handleReject}
          onCancel={() => setShowReject(false)}
        />
      )}
    </div>
  );
}
