"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";
import { PermissionGuard } from "@/components/PermissionGuard";
import { RejectModal } from "@/components/reject-modal";

interface Doc {
  id: string;
  title: string;
  doc_type: string;
  status: string;
  current_version: number;
}

interface ReviewTask {
  id: string;
  doc_id: string;
  reviewer_id: string | null;
  status: string;
  review_note: string | null;
  created_by: string;
  created_at: string;
  assigned_at: string | null;
  reviewed_at: string | null;
}

interface BatchResult {
  succeeded: string[];
  failed: { id: string; reason: string }[];
}

interface ArchMeta {
  classification_dimension?: string;
  dimension_rationale?: string;
  coverage_score?: number;
  uncovered_chunks?: string[];
}

const DIMENSION_LABELS: Record<string, string> = {
  topic: "按主题",
  process: "按流程",
  audience: "按受众",
  chronological: "按时间",
  hybrid: "混合",
};

function MeceInfoCard({ projectId }: { projectId: string }) {
  const [meta, setMeta] = useState<ArchMeta | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const resp = await api.get<{ id: string; levels_json: ArchMeta | null }[]>(
          `/v1/projects/${projectId}/architectures`,
        );
        const arch = resp.data[0];
        if (arch?.levels_json && typeof arch.levels_json === "object") {
          setMeta(arch.levels_json as ArchMeta);
        }
      } catch {
        // Non-critical
      }
    };
    load();
  }, [projectId]);

  if (!meta || !meta.classification_dimension) return null;

  const score = meta.coverage_score ?? 0;
  const scoreColor = score >= 80 ? "text-green-600" : score >= 60 ? "text-yellow-600" : "text-red-600";

  return (
    <div className="mb-6 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold text-gray-700">架构质量 (MECE)</h3>
      <div className="grid grid-cols-2 gap-4 text-sm lg:grid-cols-4">
        <div>
          <div className="text-xs text-gray-400">分类维度</div>
          <div className="font-medium text-gray-800">
            {DIMENSION_LABELS[meta.classification_dimension] || meta.classification_dimension}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-400">覆盖度</div>
          <div className={`font-bold ${scoreColor}`}>{score}%</div>
        </div>
        {meta.dimension_rationale && (
          <div className="col-span-2">
            <div className="text-xs text-gray-400">选择依据</div>
            <div className="text-gray-600">{meta.dimension_rationale}</div>
          </div>
        )}
      </div>
      {meta.uncovered_chunks && meta.uncovered_chunks.length > 0 && (
        <div className="mt-3 rounded-lg bg-yellow-50 px-3 py-2 text-xs text-yellow-700">
          未覆盖内容: {meta.uncovered_chunks.join("、")}
        </div>
      )}
    </div>
  );
}

function ReviewKanban({ projectId }: { projectId: string }) {
  const [pending, setPending] = useState<ReviewTask[]>([]);
  const [assigned, setAssigned] = useState<ReviewTask[]>([]);
  const [completed, setCompleted] = useState<ReviewTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [rejectingId, setRejectingId] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [p, a, ap, rj] = await Promise.all([
        api.get<ReviewTask[]>(`/v1/projects/${projectId}/reviews?status=pending`),
        api.get<ReviewTask[]>(`/v1/projects/${projectId}/reviews?status=assigned`),
        api.get<ReviewTask[]>(`/v1/projects/${projectId}/reviews?status=approved`),
        api.get<ReviewTask[]>(`/v1/projects/${projectId}/reviews?status=rejected`),
      ]);
      setPending(p.data);
      setAssigned(a.data);
      setCompleted([...ap.data, ...rj.data]);
    } catch {
      // Non-critical
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // Kanban action handlers (v0.52.11 — Gap-11 fix)
  const handleApprove = async (reviewId: string) => {
    setActionLoading(reviewId);
    try {
      await api.post(`/v1/projects/${projectId}/reviews/${reviewId}/approve`, {});
      await fetchAll();
    } catch { /* toast handled by api client */ }
    finally { setActionLoading(null); }
  };

  const handleReject = (reviewId: string) => {
    setRejectingId(reviewId);
  };

  const doReject = async (reviewId: string, reason: string) => {
    setRejectingId(null);
    setActionLoading(reviewId);
    try {
      await api.post(`/v1/projects/${projectId}/reviews/${reviewId}/reject`, { note: reason });
      await fetchAll();
    } catch { /* toast handled by api client */ }
    finally { setActionLoading(null); }
  };

  const handleResubmit = async (reviewId: string) => {
    setActionLoading(reviewId);
    try {
      await api.post(`/v1/projects/${projectId}/reviews/${reviewId}/resubmit`, {});
      await fetchAll();
    } catch { /* toast handled by api client */ }
    finally { setActionLoading(null); }
  };

  const KanbanCard = ({ t, column }: { t: ReviewTask; column: "pending" | "assigned" | "completed" }) => (
    <div key={t.id} className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm hover:shadow">
      <div className="text-sm font-medium text-gray-800 truncate">
        {t.doc_id.slice(0, 8)}...
      </div>
      <div className="mt-1 text-xs text-gray-400">
        {new Date(t.created_at).toLocaleDateString("zh-CN")}
      </div>
      {t.reviewer_id && (
        <div className="mt-1 text-xs text-primary-500">审批人: {t.reviewer_id.slice(0, 8)}...</div>
      )}
      {t.review_note && (
        <div className="mt-1 text-xs text-gray-500 truncate">{t.review_note}</div>
      )}
      <div className="mt-1 flex items-center justify-between">
        <StatusBadge status={t.status} />
        <div className="flex gap-1">
          {column === "assigned" && (
            <>
              <button
                onClick={() => handleApprove(t.id)}
                disabled={actionLoading === t.id}
                className="rounded bg-green-500 px-2 py-0.5 text-xs text-white hover:bg-green-600 disabled:opacity-50"
              >
                通过
              </button>
              <button
                onClick={() => handleReject(t.id)}
                disabled={actionLoading === t.id}
                className="rounded bg-red-500 px-2 py-0.5 text-xs text-white hover:bg-red-600 disabled:opacity-50"
              >
                驳回
              </button>
            </>
          )}
          {column === "completed" && t.status === "rejected" && (
            <button
              onClick={() => handleResubmit(t.id)}
              disabled={actionLoading === t.id}
              className="rounded bg-blue-500 px-2 py-0.5 text-xs text-white hover:bg-blue-600 disabled:opacity-50"
            >
              重新提交
            </button>
          )}
        </div>
      </div>
    </div>
  );

  const KanbanColumn = ({ title, tasks, color, column }: { title: string; tasks: ReviewTask[]; color: string; column: "pending" | "assigned" | "completed" }) => (
    <div className="flex-1 min-w-[280px]">
      <div className={`mb-3 flex items-center gap-2 border-b-2 ${color} pb-2`}>
        <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">{tasks.length}</span>
      </div>
      <div className="space-y-2">
        {tasks.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-200 py-6 text-center text-xs text-gray-400">
            暂无任务
          </div>
        ) : tasks.map((t) => (
          <KanbanCard key={t.id} t={t} column={column} />
        ))}
      </div>
    </div>
  );

  if (loading) return <div className="py-4 text-center text-gray-400 text-sm">加载审批看板...</div>;

  return (
    <div className="mb-8">
      <h2 className="mb-4 text-lg font-bold text-gray-900">审批看板</h2>
      <div className="flex gap-4 overflow-x-auto pb-2">
        <KanbanColumn title="待分配" tasks={pending} color="border-yellow-400" column="pending" />
        <KanbanColumn title="待审批" tasks={assigned} color="border-blue-400" column="assigned" />
        <KanbanColumn title="已完成" tasks={completed} color="border-green-400" column="completed" />
      </div>
      {rejectingId && (
        <RejectModal
          title="驳回审批"
          onConfirm={(reason) => doReject(rejectingId, reason)}
          onCancel={() => setRejectingId(null)}
        />
      )}
    </div>
  );
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
      const endpoint = `/v1/docs?project_id=${projectId}&page_size=50`;
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

      {/* Review Kanban (v0.50.3) */}
      <ReviewKanban projectId={projectId} />

      {/* MECE Architecture Quality Card */}
      <MeceInfoCard projectId={projectId} />

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
            <PermissionGuard action="edit">
              <button
                onClick={() => handleBatchAction("review")}
                className="rounded bg-primary-600 px-3 py-1 text-xs font-medium text-white hover:bg-primary-700"
              >
                批量提交审核
              </button>
            </PermissionGuard>
          )}
          {tab === "reviewing" && (
            <>
              <PermissionGuard action="publish">
                <button
                  onClick={() => handleBatchAction("publish")}
                  className="rounded bg-green-600 px-3 py-1 text-xs font-medium text-white hover:bg-green-700"
                >
                  批量通过
                </button>
              </PermissionGuard>
              <PermissionGuard action="publish">
                <button
                  onClick={() => setShowReject(true)}
                  className="rounded bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700"
                >
                  批量驳回
                </button>
              </PermissionGuard>
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
                    <Link href={`/projects/${projectId}/wiki/${doc.id}`} className="font-medium text-primary-600 hover:underline">
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
