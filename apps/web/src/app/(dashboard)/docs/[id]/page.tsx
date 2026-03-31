"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";
import { PermissionGuard } from "@/components/PermissionGuard";
import { MarkdownView } from "@/components/markdown-view";
import { VersionPanel } from "@/components/version-history/VersionPanel";

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
  summary: string | null;
  keywords: string[] | null;
  knowledge_type: string | null;
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
  const [showHistory, setShowHistory] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [summarizing, setSummarizing] = useState(false);
  const [suggestingTags, setSuggestingTags] = useState(false);
  const exportRef = useRef<HTMLDivElement>(null);

  const fetchDoc = useCallback(async () => {
    try {
      const resp = await api.get<DocDetail>(`/v1/docs/${docId}`);
      setDoc(resp.data);
      setActiveVersion(resp.data.current_version);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }, [docId]);

  useEffect(() => {
    fetchDoc();
  }, [fetchDoc]);

  // Close export menu on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) {
        setShowExportMenu(false);
      }
    };
    if (showExportMenu) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [showExportMenu]);

  const handleExport = async (fmt: "markdown" | "pdf" | "docx") => {
    setShowExportMenu(false);
    setExporting(true);
    setActionMsg("");
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const resp = await fetch(`${apiBase}/v1/docs/${docId}/export?format=${fmt}`, {
        credentials: "include",
      });
      if (!resp.ok) {
        throw new Error(`导出失败 (${resp.status})`);
      }
      const blob = await resp.blob();
      const disposition = resp.headers.get("Content-Disposition") || "";
      const filenameMatch = disposition.match(/filename="?([^"]+)"?/);
      const filename = filenameMatch ? filenameMatch[1] : `document.${fmt === "markdown" ? "md" : fmt}`;

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : "导出失败");
    } finally {
      setExporting(false);
    }
  };

  const handleAiSummarize = async () => {
    setSummarizing(true);
    setActionMsg("");
    try {
      await api.post(`/v1/docs/${docId}/ai-summarize`, {});
      await fetchDoc();
      setActionMsg("操作成功");
    } catch (e) {
      setActionMsg(e instanceof ApiClientError ? e.message : "摘要生成失败");
    } finally {
      setSummarizing(false);
    }
  };

  const handleAiSuggestTags = async () => {
    setSuggestingTags(true);
    setActionMsg("");
    try {
      await api.post(`/v1/docs/${docId}/ai-suggest-tags`, {});
      await fetchDoc();
      setActionMsg("操作成功");
    } catch (e) {
      setActionMsg(e instanceof ApiClientError ? e.message : "标签推荐失败");
    } finally {
      setSuggestingTags(false);
    }
  };

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
    <div className="flex gap-0">
    <div className={`flex-1 ${showHistory ? "" : "mx-auto max-w-4xl"}`}>
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
            <PermissionGuard action="edit">
              <Link href={`/docs/${docId}/edit`} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">
                编辑内容
              </Link>
            </PermissionGuard>
            <PermissionGuard action="edit">
              <button onClick={() => handleAction("review")} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
                提交审核
              </button>
            </PermissionGuard>
          </>
        )}
        {doc.status === "reviewing" && (
          <PermissionGuard action="publish">
            <button onClick={() => handleAction("publish")} className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700">
              发布
            </button>
          </PermissionGuard>
        )}
        {doc.current_version > 1 && (
          <Link href={`/docs/${docId}/diff?from=1&to=${doc.current_version}`} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
            版本对比
          </Link>
        )}
        {/* Export dropdown */}
        <div ref={exportRef} className="relative">
          <button
            onClick={() => setShowExportMenu(!showExportMenu)}
            disabled={exporting}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {exporting ? "导出中..." : "导出 ▾"}
          </button>
          {showExportMenu && (
            <div className="absolute left-0 top-full z-10 mt-1 w-40 rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
              <button onClick={() => handleExport("markdown")} className="block w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50">
                Markdown (.md)
              </button>
              <button onClick={() => handleExport("pdf")} className="block w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50">
                PDF (.pdf)
              </button>
              <button onClick={() => handleExport("docx")} className="block w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50">
                Word (.docx)
              </button>
            </div>
          )}
        </div>
        <button
          onClick={() => setShowHistory(!showHistory)}
          className={`rounded-lg border px-4 py-2 text-sm ${showHistory ? "border-primary-300 bg-primary-50 text-primary-700" : "border-gray-300 text-gray-700 hover:bg-gray-50"}`}
        >
          历史版本
        </button>
      </div>

      {/* Summary */}
      <div className="mb-4 rounded-lg border border-gray-200 bg-white p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-600">摘要</h3>
          <PermissionGuard action="edit">
            <button
              onClick={handleAiSummarize}
              disabled={summarizing}
              className="rounded border border-gray-300 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-50"
            >
              {summarizing ? "生成中..." : doc.summary ? "重新生成" : "生成摘要"}
            </button>
          </PermissionGuard>
        </div>
        <p className="mt-2 text-sm text-gray-700">
          {doc.summary || <span className="text-gray-400">暂无摘要</span>}
        </p>
      </div>

      {/* Keywords */}
      <div className="mb-4 rounded-lg border border-gray-200 bg-white p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-600">关键词</h3>
          <PermissionGuard action="edit">
            <button
              onClick={handleAiSuggestTags}
              disabled={suggestingTags}
              className="rounded border border-gray-300 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-50"
            >
              {suggestingTags ? "推荐中..." : doc.keywords?.length ? "刷新标签" : "推荐标签"}
            </button>
          </PermissionGuard>
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          {doc.keywords && doc.keywords.length > 0 ? (
            doc.keywords.map((kw) => (
              <span key={kw} className="rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-600">
                {kw}
              </span>
            ))
          ) : (
            <span className="text-sm text-gray-400">暂无关键词</span>
          )}
        </div>
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

    {/* Version History Panel */}
    {showHistory && (
      <div className="w-96 flex-shrink-0">
        <VersionPanel
          docId={docId}
          currentVersion={doc.current_version}
          onClose={() => setShowHistory(false)}
          onRollbackSuccess={() => {
            setShowHistory(false);
            fetchDoc();
          }}
        />
      </div>
    )}
    </div>
  );
}
