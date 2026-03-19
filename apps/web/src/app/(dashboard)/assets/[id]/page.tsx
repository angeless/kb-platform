"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, ApiClientError } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

interface AssetDetail {
  id: string;
  filename: string;
  asset_type: string;
  parse_status: string;
  file_size: number | null;
  source_url: string | null;
  file_hash: string | null;
  uploaded_at: string;
  chunks?: Chunk[];
}

interface Chunk {
  id: string;
  chunk_index: number;
  content_text: string;
  page_or_timestamp: string | null;
  tags: Record<string, unknown> | null;
}

export default function AssetDetailPage() {
  const params = useParams();
  const assetId = params.id as string;

  const [asset, setAsset] = useState<AssetDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetch = async () => {
      try {
        const resp = await api.get<AssetDetail>(`/v1/assets/${assetId}`);
        setAsset(resp.data);
      } catch (e) {
        setError(e instanceof ApiClientError ? e.message : "加载失败");
      } finally {
        setIsLoading(false);
      }
    };
    fetch();
  }, [assetId]);

  if (isLoading) return <div className="py-12 text-center text-gray-400">加载中...</div>;
  if (error || !asset) return <div className="py-12 text-center text-red-500">{error}</div>;

  return (
    <div className="mx-auto max-w-4xl">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-900">{asset.filename}</h1>
          <StatusBadge status={asset.parse_status} />
        </div>
        <div className="mt-2 flex gap-4 text-sm text-gray-500">
          <span>类型：{asset.asset_type}</span>
          {asset.file_size && (
            <span>大小：{(asset.file_size / 1024 / 1024).toFixed(2)} MB</span>
          )}
          <span>上传于 {new Date(asset.uploaded_at).toLocaleString("zh-CN")}</span>
        </div>
        {asset.source_url && (
          <p className="mt-1 text-sm text-gray-400">来源：{asset.source_url}</p>
        )}
      </div>

      {/* Parsed Chunks */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-200 px-5 py-4">
          <h2 className="font-semibold text-gray-900">
            解析片段 {asset.chunks ? `(${asset.chunks.length})` : ""}
          </h2>
        </div>

        {!asset.chunks || asset.chunks.length === 0 ? (
          <div className="px-5 py-8 text-center text-gray-400">
            {asset.parse_status === "pending"
              ? "等待解析..."
              : asset.parse_status === "parsing"
                ? "正在解析..."
                : asset.parse_status === "failed"
                  ? "解析失败"
                  : asset.parse_status === "unsupported"
                    ? "此文件类型暂不支持自动解析，文件已保存"
                    : "暂无解析结果"}
          </div>
        ) : (
          <ul>
            {asset.chunks.map((chunk) => (
              <li
                key={chunk.id}
                className="border-b border-gray-100 px-5 py-4 last:border-0"
              >
                <div className="mb-1 flex items-center gap-2 text-xs text-gray-400">
                  <span>片段 #{chunk.chunk_index + 1}</span>
                  {chunk.page_or_timestamp && (
                    <span>· {chunk.page_or_timestamp}</span>
                  )}
                </div>
                <p className="whitespace-pre-wrap text-sm text-gray-700">
                  {chunk.content_text}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
