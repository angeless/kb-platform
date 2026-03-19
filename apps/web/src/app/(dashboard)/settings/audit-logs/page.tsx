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
  upload: "上传", import_url: "URL导入", import_archive: "压缩包导入",
  review: "提交审核", publish: "发布", reject: "驳回",
  edit: "编辑", assign_node: "分配节点", resolve: "解决冲突",
  create: "创建",
};

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [action, setAction] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchLogs = useCallback(async () => {
    setIsLoading(true);
    try {
      let url = `/v1/audit-logs?page=${page}&page_size=30`;
      if (action) url += `&action=${action}`;
      const resp = await api.get<AuditEntry[]>(url);
      setLogs(resp.data);
      setTotal(resp.meta?.total ?? 0);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }, [page, action]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  const totalPages = Math.ceil(total / 30);

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">审计日志</h1>

      {/* Filter */}
      <div className="mb-4 flex gap-3">
        <select
          value={action}
          onChange={(e) => { setAction(e.target.value); setPage(1); }}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
        >
          <option value="">全部操作</option>
          {Object.entries(actionLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <span className="py-2 text-sm text-gray-500">共 {total} 条记录</span>
      </div>

      {error && <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

      {isLoading ? (
        <div className="py-12 text-center text-gray-400">加载中...</div>
      ) : logs.length === 0 ? (
        <div className="py-12 text-center text-gray-400">暂无审计记录</div>
      ) : (
        <>
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-200 bg-gray-50">
                <tr>
                  <th className="px-5 py-3 text-left font-medium text-gray-600">时间</th>
                  <th className="px-5 py-3 text-left font-medium text-gray-600">操作</th>
                  <th className="px-5 py-3 text-left font-medium text-gray-600">资源类型</th>
                  <th className="px-5 py-3 text-left font-medium text-gray-600">资源 ID</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id} className="border-b border-gray-100 last:border-0">
                    <td className="px-5 py-3 text-gray-400 whitespace-nowrap">
                      {new Date(log.created_at).toLocaleString("zh-CN")}
                    </td>
                    <td className="px-5 py-3">
                      <span className="inline-flex rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                        {actionLabels[log.action] || log.action}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-gray-500">{log.resource_type}</td>
                    <td className="px-5 py-3 font-mono text-xs text-gray-400">{log.resource_id.slice(0, 8)}...</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-center gap-2">
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50">上一页</button>
              <span className="text-sm text-gray-500">{page} / {totalPages}</span>
              <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50">下一页</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
