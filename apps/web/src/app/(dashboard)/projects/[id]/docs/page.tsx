"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { StatusBadge } from "@/components/status-badge";
import { PermissionGuard } from "@/components/PermissionGuard";
import { useDocs } from "@/hooks/useDocs";

export default function ProjectDocsPage() {
  const params = useParams();
  const projectId = params.id as string;
  const [page, setPage] = useState(1);

  const { data, isLoading, error } = useDocs(projectId, page);
  const docs = data?.data ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / 20);

  return (
    <div>
      <div className="mb-4">
        <Link href={`/projects/${projectId}`} className="text-sm text-primary-600 hover:underline">
          ← 返回项目
        </Link>
      </div>

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">知识文档</h1>
          <p className="mt-1 text-sm text-gray-500">共 {total} 篇文档</p>
        </div>
        <Link
          href={`/projects/${projectId}/docs/pending`}
          className="rounded-lg border border-orange-300 px-4 py-2 text-sm text-orange-600 hover:bg-orange-50"
        >
          待分配文档池
        </Link>
      </div>

      {error && <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error instanceof Error ? error.message : "加载失败"}</div>}

      {isLoading ? (
        <div className="py-12 text-center text-gray-400">加载中...</div>
      ) : docs.length === 0 ? (
        <div className="py-12 text-center text-gray-400">暂无文档。系统解析资料后会自动生成文档草稿。</div>
      ) : (
        <>
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-200 bg-gray-50">
                <tr>
                  <th className="px-5 py-3 text-left font-medium text-gray-600">标题</th>
                  <th className="px-5 py-3 text-left font-medium text-gray-600">类型</th>
                  <th className="px-5 py-3 text-left font-medium text-gray-600">版本</th>
                  <th className="px-5 py-3 text-left font-medium text-gray-600">状态</th>
                  <th className="px-5 py-3 text-left font-medium text-gray-600">操作</th>
                </tr>
              </thead>
              <tbody>
                {docs.map((doc) => (
                  <tr key={doc.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                    <td className="px-5 py-3">
                      <Link href={`/docs/${doc.id}`} className="font-medium text-primary-600 hover:underline">
                        {doc.title}
                      </Link>
                      {!doc.node_id && (
                        <span className="ml-2 text-xs text-orange-500">未分配</span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-gray-500">{doc.doc_type}</td>
                    <td className="px-5 py-3 text-gray-500">v{doc.current_version}</td>
                    <td className="px-5 py-3"><StatusBadge status={doc.status} /></td>
                    <td className="px-5 py-3">
                      <div className="flex gap-2">
                        <PermissionGuard action="edit">
                          {doc.status === "draft" && (
                            <Link href={`/docs/${doc.id}/edit`} className="text-xs text-primary-600 hover:underline">
                              编辑
                            </Link>
                          )}
                        </PermissionGuard>
                        {doc.current_version > 1 && (
                          <Link href={`/docs/${doc.id}/diff?from=1&to=${doc.current_version}`} className="text-xs text-gray-500 hover:underline">
                            对比
                          </Link>
                        )}
                      </div>
                    </td>
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
