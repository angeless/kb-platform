"use client";

import { useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useVirtualizer } from "@tanstack/react-virtual";
import { StatusBadge } from "@/components/status-badge";
import { PermissionGuard } from "@/components/PermissionGuard";
import { useDocs } from "@/hooks/useDocs";

const PAGE_SIZE = 100;
const ROW_HEIGHT = 45;
const MAX_VISIBLE_ROWS = 15;

export default function ProjectDocsPage() {
  const params = useParams();
  const projectId = params.id as string;
  const [page, setPage] = useState(1);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { data, isLoading, error } = useDocs(projectId, page, PAGE_SIZE);
  const docs = data?.data ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  const rowVirtualizer = useVirtualizer({
    count: docs.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 10,
  });

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
            {/* Fixed table header */}
            <div className="border-b border-gray-200 bg-gray-50">
              <div className="flex text-sm font-medium text-gray-600">
                <div className="w-[40%] px-5 py-3">标题</div>
                <div className="w-[15%] px-5 py-3">类型</div>
                <div className="w-[10%] px-5 py-3">版本</div>
                <div className="w-[15%] px-5 py-3">状态</div>
                <div className="w-[20%] px-5 py-3">操作</div>
              </div>
            </div>

            {/* Virtualized scrollable body */}
            <div
              ref={scrollRef}
              className="overflow-auto"
              style={{ maxHeight: `${Math.min(docs.length, MAX_VISIBLE_ROWS) * ROW_HEIGHT}px` }}
            >
              <div
                style={{ height: `${rowVirtualizer.getTotalSize()}px`, position: "relative" }}
              >
                {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                  const doc = docs[virtualRow.index];
                  return (
                    <div
                      key={doc.id}
                      className="absolute left-0 flex w-full items-center border-b border-gray-100 text-sm hover:bg-gray-50"
                      style={{
                        height: `${virtualRow.size}px`,
                        transform: `translateY(${virtualRow.start}px)`,
                      }}
                    >
                      <div className="w-[40%] truncate px-5">
                        <Link href={`/docs/${doc.id}`} className="font-medium text-primary-600 hover:underline">
                          {doc.title}
                        </Link>
                        {!doc.node_id && (
                          <span className="ml-2 text-xs text-orange-500">未分配</span>
                        )}
                      </div>
                      <div className="w-[15%] px-5 text-gray-500">{doc.doc_type}</div>
                      <div className="w-[10%] px-5 text-gray-500">v{doc.current_version}</div>
                      <div className="w-[15%] px-5"><StatusBadge status={doc.status} /></div>
                      <div className="w-[20%] px-5">
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
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
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
