"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiClientError } from "@/lib/api";
import { usePermission } from "@/hooks/usePermission";
import { useRouter } from "next/navigation";

interface AuditLog {
  id: string;
  user_id: string;
  project_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string;
  detail: Record<string, unknown> | null;
  created_at: string;
}

const ACTION_LABELS: Record<string, string> = {
  create_doc: "创建文档",
  update_doc: "更新文档",
  rollback_doc: "回滚文档",
  delete_doc: "删除文档",
  create_project: "创建项目",
  update_project: "更新项目",
  delete_project: "删除项目",
  invite_user: "邀请用户",
  update_user_role: "修改角色",
  remove_user: "移除用户",
  create_provider: "创建模型提供商",
};

const RESOURCE_TYPE_LABELS: Record<string, string> = {
  knowledge_doc: "知识文档",
  project: "项目",
  user: "用户",
  model_provider: "模型提供商",
};

const ACTION_OPTIONS = Object.entries(ACTION_LABELS);
const RESOURCE_OPTIONS = Object.entries(RESOURCE_TYPE_LABELS);

export default function AuditLogsPage() {
  const { hasRole } = usePermission();
  const router = useRouter();

  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // Filters
  const [filterAction, setFilterAction] = useState("");
  const [filterResourceType, setFilterResourceType] = useState("");

  // Permission guard
  useEffect(() => {
    if (!hasRole("tenant_admin")) {
      router.replace("/projects");
    }
  }, [hasRole, router]);

  const fetchLogs = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("page_size", String(pageSize));
      if (filterAction) params.set("action", filterAction);
      if (filterResourceType) params.set("resource_type", filterResourceType);

      const resp = await api.get<AuditLog[]>(
        `/v1/audit-logs?${params.toString()}`,
      );
      setLogs(resp.data);
      setTotal(resp.meta?.total ?? 0);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "加载审计日志失败");
    } finally {
      setIsLoading(false);
    }
  }, [page, filterAction, filterResourceType]);

  useEffect(() => {
    if (hasRole("tenant_admin")) {
      fetchLogs();
    }
  }, [fetchLogs, hasRole]);

  const totalPages = Math.ceil(total / pageSize);

  if (!hasRole("tenant_admin")) {
    return null;
  }

  return (
    <div className="mx-auto max-w-6xl">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">操作日志</h1>

      {/* Filters */}
      <div className="mb-4 flex gap-4">
        <select
          value={filterAction}
          onChange={(e) => { setFilterAction(e.target.value); setPage(1); }}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        >
          <option value="">全部操作</option>
          {ACTION_OPTIONS.map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
        <select
          value={filterResourceType}
          onChange={(e) => { setFilterResourceType(e.target.value); setPage(1); }}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        >
          <option value="">全部资源类型</option>
          {RESOURCE_OPTIONS.map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>
      )}

      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">时间</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">用户</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">操作</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">资源类型</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">资源 ID</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-400">
                  加载中...
                </td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-400">
                  暂无日志记录
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {new Date(log.created_at).toLocaleString("zh-CN")}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {log.user_id.slice(0, 8)}...
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                      {ACTION_LABELS[log.action] ?? log.action}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {RESOURCE_TYPE_LABELS[log.resource_type] ?? log.resource_type}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-400 font-mono">
                    {log.resource_id.slice(0, 12)}...
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <span className="text-sm text-gray-500">
            共 {total} 条记录，第 {page}/{totalPages} 页
          </span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              上一页
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              下一页
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
