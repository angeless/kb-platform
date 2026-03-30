"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";
import { FileUpload } from "@/components/file-upload";
import { BatchDropzone } from "@/components/batch-import/BatchDropzone";
import { BatchProgressList } from "@/components/batch-import/BatchProgressList";

interface Asset {
  id: string;
  filename: string;
  asset_type: string;
  parse_status: string;
  file_size: number | null;
  uploaded_at: string;
}

export default function ProjectAssetsPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [assets, setAssets] = useState<Asset[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [showUpload, setShowUpload] = useState(false);
  const [showBatch, setShowBatch] = useState(false);
  const [batchId, setBatchId] = useState<string | null>(null);

  const fetchAssets = useCallback(async () => {
    setIsLoading(true);
    try {
      const resp = await api.get<Asset[]>(
        `/v1/assets?project_id=${projectId}&page=${page}&page_size=20`,
      );
      setAssets(resp.data);
      setTotal(resp.meta?.total ?? 0);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }, [projectId, page]);

  useEffect(() => {
    fetchAssets();
  }, [fetchAssets]);

  const formatSize = (bytes: number | null) => {
    if (!bytes) return "—";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

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
          <h1 className="text-2xl font-bold text-gray-900">资料管理</h1>
          <p className="mt-1 text-sm text-gray-500">共 {total} 份资料</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => { setShowBatch(!showBatch); if (showUpload) setShowUpload(false); }}
            className="rounded-lg border border-primary-600 px-4 py-2 text-sm font-medium text-primary-600 hover:bg-primary-50"
          >
            批量导入
          </button>
          <button
            onClick={() => { setShowUpload(!showUpload); if (showBatch) setShowBatch(false); }}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            上传资料
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>
      )}

      {showUpload && (
        <div className="mb-6">
          <FileUpload projectId={projectId} onUploadComplete={fetchAssets} />
        </div>
      )}

      {showBatch && !batchId && (
        <div className="mb-6">
          <BatchDropzone
            projectId={projectId}
            onBatchCreated={(id) => setBatchId(id)}
          />
        </div>
      )}

      {batchId && (
        <div className="mb-6">
          <BatchProgressList
            projectId={projectId}
            batchId={batchId}
            onComplete={() => {
              fetchAssets();
            }}
          />
        </div>
      )}

      {isLoading ? (
        <div className="py-12 text-center text-gray-400">加载中...</div>
      ) : assets.length === 0 ? (
        <div className="py-12 text-center text-gray-400">
          还没有资料，点击"上传资料"开始
        </div>
      ) : (
        <>
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-200 bg-gray-50">
                <tr>
                  <th className="px-5 py-3 text-left font-medium text-gray-600">文件名</th>
                  <th className="px-5 py-3 text-left font-medium text-gray-600">类型</th>
                  <th className="px-5 py-3 text-left font-medium text-gray-600">大小</th>
                  <th className="px-5 py-3 text-left font-medium text-gray-600">状态</th>
                  <th className="px-5 py-3 text-left font-medium text-gray-600">上传时间</th>
                </tr>
              </thead>
              <tbody>
                {assets.map((asset) => (
                  <tr key={asset.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                    <td className="px-5 py-3">
                      <Link
                        href={`/assets/${asset.id}`}
                        className="font-medium text-primary-600 hover:underline"
                      >
                        {asset.filename}
                      </Link>
                    </td>
                    <td className="px-5 py-3 text-gray-500">{asset.asset_type}</td>
                    <td className="px-5 py-3 text-gray-500">{formatSize(asset.file_size)}</td>
                    <td className="px-5 py-3">
                      <StatusBadge status={asset.parse_status} />
                    </td>
                    <td className="px-5 py-3 text-gray-400">
                      {new Date(asset.uploaded_at).toLocaleDateString("zh-CN")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50"
              >
                上一页
              </button>
              <span className="text-sm text-gray-500">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50"
              >
                下一页
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
