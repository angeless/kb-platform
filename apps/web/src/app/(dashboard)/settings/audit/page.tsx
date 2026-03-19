"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiClientError } from "@/lib/api";

interface AuditEntry {
  id: string;
  user_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  detail: Record<string, unknown> | null;
  created_at: string;
}

const actionLabels: Record<string, string> = {
  upload: "上传资料",
  import_url: "URL 导入",
  import_archive: "压缩包导入",
  review: "提交审核",
  publish: "发布",
  reject: "驳回",
  edit: "编辑内容",
  assign_node: "绑定节点",
  resolve: "解决冲突",
  create: "创建",
};

const resourceLabels: Record<string, string> = {
  asset: "资料",
  knowledge_doc: "知识文档",
  architecture: "知识架构",
  conflict: "冲突",
  model_provider: "模型供应商",
};

export default function AuditLogPage() {
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // Filters
  const [filterAction, setFilterAction] = useState("");
  const [filterResource, setFilterResource] = useState("");

  const fetchLogs = useCallback(async () => {
    setIsLoading(true);
    try {
      let url = `/v1/audit-logs?page=${page}&page_size=20`;
      if (filterAction) url += `&action=${filterAction}`;
      if (filterResource) url += `&resource_type=${filterResource}`;
      const resp = await api.get<AuditEntry[]>(url);
      setLogs(resp.data);
      setTotal(resp.meta?.total ?? 0);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }, [page, filterAction, filterResource]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  const totalPages = Math.ceil(total / 20);

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">审计日志</h1>

      {error && <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

      {/* Filters */}
      <div className="mb-4 flex gap-3">
        <select value={filterAction} onChange={(e) => { setFilterAction(e.target.value); setPage(1); }}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
          <option value="">所有操作</option>
          {Object.entries(actionLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={filterResource} onChange={(e) => { setFilterResource(e.target.value); setPage(1); }}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
          <option value="">所有资源</option>
          {Object.entries(resourceLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <span className="self-center text-sm text-gray-500">共 {total} 条记录</span>
      </div>

      {/* Log Table */}
      {isLoading ? (
        <div className="py-12 text-center text-gray-400">加载中...</div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="border-b border-gray-200 bg-gray-50">
              <tr>
                <th className="px-5 py-3 text-left font-medium text-gray-600">时间</th>
                <th className="px-5 py-3 text-left font-medium text-gray-600">操作</th>
                <th className="px-5 py-3 text-left font-medium text-gray-600">资源类型</th>
                <th className="px-5 py-3 text-left font-medium text-gray-600">资源 ID</th>
                <th className="px-5 py-3 text-left font-medium text-gray-600">详情</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 ? (
                <tr><td colSpan={5} className="px-5 py-8 text-center text-gray-400">暂无日志</td></tr>
              ) : logs.map((log) => (
                <tr key={log.id} className="border-b border-gray-100 last:border-0">
                  <td className="px-5 py-3 text-gray-500 whitespace-nowrap">
                    {new Date(log.created_at).toLocaleString("zh-CN")}
                  </td>
                  <td className="px-5 py-3">
                    <span className="inline-flex rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                      {actionLabels[log.action] || log.action}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-gray-500">{resourceLabels[log.resource_type] || log.resource_type}</td>
                  <td className="px-5 py-3 font-mono text-xs text-gray-400">{log.resource_id.slice(0, 8)}...</td>
                  <td className="px-5 py-3 text-xs text-gray-400">
                    {log.detail ? JSON.stringify(log.detail).slice(0, 50) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-center gap-2">
          <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
            className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50">上一页</button>
          <span className="text-sm text-gray-500">{page} / {totalPages}</span>
          <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}
            className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50">下一页</button>
        </div>
      )}
    </div>
  );
}
