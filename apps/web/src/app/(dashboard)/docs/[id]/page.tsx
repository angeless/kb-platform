"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";
import { MarkdownView } from "@/components/markdown-view";

interface SourceRef {
  id: string;
  asset_chunk_id: string;
  location_hint: string | null;
}

interface DocVersion {
  id: string;
  version: number;
  content_md: string;
  change_reason: string | null;
  created_at: string;
  source_refs: SourceRef[];
}

interface DocDetail {
  id: string;
  project_id: string;
  node_id: string | null;
  doc_type: string;
  title: string;
  current_version: number;
  status: string;
  versions: DocVersion[];
}

export default function DocDetailPage() {
  const params = useParams();
  const docId = params.id as string;

  const [doc, setDoc] = useState<DocDetail | null>(null);
  const [activeVersion, setActiveVersion] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionMsg, setActionMsg] = useState("");

  useEffect(() => {
    const fetchDoc = async () => {
      try {
        const resp = await api.get<DocDetail>(`/v1/docs/${docId}`);
        setDoc(resp.data);
        setActiveVersion(resp.data.current_version);
      } catch (e) {
        setError(e instanceof ApiClientError ? e.message : "加载失败");
      } finally {
        setIsLoading(false);
      }
    };
    fetchDoc();
  }, [docId]);

  const handleAction = async (action: string) => {
    setActionMsg("");
    try {
      if (action === "review") {
        await api.post(`/v1/docs/${docId}/review`, {});
      } else if (action === "publish") {
        await api.post(`/v1/docs/${docId}/publish`, {});
      }
      // Refresh
      const resp = await api.get<DocDetail>(`/v1/docs/${docId}`);
      setDoc(resp.data);
      setActionMsg("操作成功");
    } catch (e) {
      setActionMsg(e instanceof ApiClientError ? e.message : "操作失败");
    }
  };

  if (isLoading) return <div className="py-12 text-center text-gray-400">加载中...</div>;
  if (error || !doc) return <div className="py-12 text-center text-red-500">{error}</div>;

  const currentVer = doc.versions.find((v) => v.version === activeVersion);

  return (
    <div className="mx-auto max-w-4xl">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-900">{doc.title}</h1>
          <StatusBadge status={doc.status} />
        </div>
        <div className="mt-2 flex gap-4 text-sm text-gray-500">
          <span>类型：{doc.doc_type}</span>
          <span>版本：v{doc.current_version}</span>
          {!doc.node_id && <span className="text-orange-500">未分配到架构节点</span>}
        </div>
      </div>

      {actionMsg && (
        <div className={`mb-4 rounded-lg p-3 text-sm ${actionMsg === "操作成功" ? "bg-green-50 text-green-600" : "bg-red-50 text-red-600"}`}>
          {actionMsg}
        </div>
      )}

      {/* Action Bar */}
      <div className="mb-6 flex gap-2">
        {doc.status === "draft" && (
          <>
            <Link href={`/docs/${docId}/edit`} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">
              编辑内容
            </Link>
            <button onClick={() => handleAction("review")} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
              提交审核
            </button>
          </>
        )}
        {doc.status === "reviewing" && (
          <button onClick={() => handleAction("publish")} className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700">
            发布
          </button>
        )}
        {doc.current_version > 1 && (
          <Link href={`/docs/${docId}/diff?from=1&to=${doc.current_version}`} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
            版本对比
          </Link>
        )}
      </div>

      {/* Version Tabs */}
      {doc.versions.length > 1 && (
        <div className="mb-4 flex gap-1 overflow-x-auto border-b border-gray-200">
          {doc.versions
            .sort((a, b) => b.version - a.version)
            .map((v) => (
              <button
                key={v.version}
                onClick={() => setActiveVersion(v.version)}
                className={`whitespace-nowrap border-b-2 px-4 py-2 text-sm ${
                  activeVersion === v.version
                    ? "border-primary-600 font-medium text-primary-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                v{v.version}
              </button>
            ))}
        </div>
      )}

      {/* Content */}
      {currentVer ? (
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          {currentVer.change_reason && (
            <div className="mb-4 rounded-lg bg-gray-50 p-3 text-sm text-gray-500">
              变更原因：{currentVer.change_reason}
            </div>
          )}
          <MarkdownView content={currentVer.content_md} />

          {/* Source Refs */}
          {currentVer.source_refs.length > 0 && (
            <div className="mt-6 border-t border-gray-200 pt-4">
              <h3 className="mb-2 text-sm font-semibold text-gray-600">来源引用</h3>
              <ul className="space-y-1">
                {currentVer.source_refs.map((ref, i) => (
                  <li key={ref.id} className="text-xs text-gray-400">
                    [{i}] 资料片段 {ref.asset_chunk_id.slice(0, 8)}...
                    {ref.location_hint && ` · ${ref.location_hint}`}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        <div className="py-8 text-center text-gray-400">暂无内容</div>
      )}
    </div>
  );
}
