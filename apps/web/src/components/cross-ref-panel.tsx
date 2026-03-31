"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";
import { PermissionGuard } from "@/components/PermissionGuard";

interface CrossRef {
  id: string;
  source_doc_id: string;
  target_doc_id: string;
  relation_type: string;
  confidence: number;
  note: string | null;
  source_title: string | null;
  target_title: string | null;
  target_project_id: string | null;
  target_project_name: string | null;
}

interface Suggestion {
  target_doc_id: string;
  target_title: string;
  relation_type: string;
  confidence: number;
  reason: string;
}

interface DocItem {
  id: string;
  title: string;
}

const RELATION_LABELS: Record<string, string> = {
  related: "相关",
  depends_on: "依赖",
  extends: "扩展",
  contradicts: "矛盾",
  supersedes: "替代",
};

const RELATION_OPTIONS = Object.entries(RELATION_LABELS);

interface CrossRefPanelProps {
  docId: string;
  projectId: string;
}

export function CrossRefPanel({ docId, projectId }: CrossRefPanelProps) {
  const [crossRefs, setCrossRefs] = useState<CrossRef[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Add modal state
  const [showAddModal, setShowAddModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<DocItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<DocItem | null>(null);
  const [relationType, setRelationType] = useState("related");
  const [note, setNote] = useState("");
  const [creating, setCreating] = useState(false);

  // AI suggest state
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [suggesting, setSuggesting] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);

  const [actionMsg, setActionMsg] = useState("");

  const fetchRefs = useCallback(async () => {
    try {
      const resp = await api.get<CrossRef[]>(`/v1/cross-refs/doc/${docId}`);
      setCrossRefs(resp.data);
    } catch {
      // Non-critical
    } finally {
      setLoading(false);
    }
  }, [docId]);

  useEffect(() => {
    fetchRefs();
  }, [fetchRefs]);

  const handleDelete = async (refId: string) => {
    setActionMsg("");
    try {
      await api.del(`/v1/cross-refs/${refId}`);
      setCrossRefs((prev) => prev.filter((r) => r.id !== refId));
    } catch (e) {
      setActionMsg(e instanceof ApiClientError ? e.message : "删除失败");
    }
  };

  // Search docs for add modal
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const resp = await api.get<DocItem[]>(
        `/v1/docs?project_id=${projectId}&page_size=10`,
      );
      // Client-side filter by title match
      const filtered = resp.data.filter(
        (d) => d.id !== docId && d.title.toLowerCase().includes(searchQuery.toLowerCase()),
      );
      setSearchResults(filtered);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  const handleCreate = async () => {
    if (!selectedDoc) return;
    setCreating(true);
    setActionMsg("");
    try {
      await api.post("/v1/cross-refs", {
        source_doc_id: docId,
        target_doc_id: selectedDoc.id,
        relation_type: relationType,
        confidence: 1.0,
        note: note || null,
      });
      setShowAddModal(false);
      setSelectedDoc(null);
      setSearchQuery("");
      setSearchResults([]);
      setNote("");
      setRelationType("related");
      await fetchRefs();
    } catch (e) {
      setActionMsg(e instanceof ApiClientError ? e.message : "创建失败");
    } finally {
      setCreating(false);
    }
  };

  const handleAiSuggest = async () => {
    setSuggesting(true);
    setShowSuggestions(true);
    setSuggestions([]);
    try {
      const resp = await api.post<Suggestion[]>("/v1/cross-refs/auto-suggest", {
        doc_id: docId,
        max_results: 5,
      });
      setSuggestions(resp.data);
    } catch (e) {
      setActionMsg(e instanceof ApiClientError ? e.message : "AI 建议失败");
    } finally {
      setSuggesting(false);
    }
  };

  const handleAcceptSuggestion = async (suggestion: Suggestion) => {
    setActionMsg("");
    try {
      await api.post("/v1/cross-refs", {
        source_doc_id: docId,
        target_doc_id: suggestion.target_doc_id,
        relation_type: suggestion.relation_type,
        confidence: suggestion.confidence,
        note: suggestion.reason,
      });
      setSuggestions((prev) =>
        prev.filter((s) => s.target_doc_id !== suggestion.target_doc_id),
      );
      await fetchRefs();
    } catch (e) {
      setActionMsg(e instanceof ApiClientError ? e.message : "创建失败");
    }
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-600">关联文档</h3>
        <div className="flex gap-2">
          <PermissionGuard action="edit">
            <button
              onClick={handleAiSuggest}
              disabled={suggesting}
              className="rounded border border-gray-300 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-50"
            >
              {suggesting ? "分析中..." : "AI 建议关联"}
            </button>
          </PermissionGuard>
          <PermissionGuard action="edit">
            <button
              onClick={() => setShowAddModal(true)}
              className="rounded border border-gray-300 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50"
            >
              添加关联
            </button>
          </PermissionGuard>
        </div>
      </div>

      {actionMsg && (
        <div className="mt-2 text-xs text-red-500">{actionMsg}</div>
      )}

      {/* Cross-ref list */}
      <div className="mt-3">
        {loading ? (
          <p className="text-xs text-gray-400">加载中...</p>
        ) : crossRefs.length === 0 ? (
          <p className="text-xs text-gray-400">暂无关联文档</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {crossRefs.map((ref) => {
              const isSource = ref.source_doc_id === docId;
              const linkedDocId = isSource ? ref.target_doc_id : ref.source_doc_id;
              const linkedTitle = isSource
                ? ref.target_title
                : ref.source_title;
              return (
                <li
                  key={ref.id}
                  className="flex items-center justify-between py-2"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="shrink-0 rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500">
                      {isSource ? "" : "← "}
                      {RELATION_LABELS[ref.relation_type] || ref.relation_type}
                    </span>
                    <Link
                      href={`/docs/${linkedDocId}`}
                      className="truncate text-sm text-blue-600 hover:underline"
                    >
                      {linkedTitle || linkedDocId.slice(0, 8)}
                    </Link>
                    {ref.target_project_id &&
                      ref.target_project_id !== projectId && (
                        <span className="shrink-0 rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-600">
                          {ref.target_project_name}
                        </span>
                      )}
                    <span className="shrink-0 text-xs text-gray-400">
                      {Math.round(ref.confidence * 100)}%
                    </span>
                  </div>
                  <PermissionGuard action="edit">
                    <button
                      onClick={() => handleDelete(ref.id)}
                      className="ml-2 shrink-0 text-xs text-red-400 hover:text-red-600"
                    >
                      删除
                    </button>
                  </PermissionGuard>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* AI Suggestions */}
      {showSuggestions && (
        <div className="mt-4 rounded-lg border border-blue-100 bg-blue-50 p-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-semibold text-blue-700">AI 建议</h4>
            <button
              onClick={() => setShowSuggestions(false)}
              className="text-xs text-gray-400 hover:text-gray-600"
            >
              关闭
            </button>
          </div>
          {suggesting ? (
            <p className="mt-2 text-xs text-blue-500">正在分析文档关联...</p>
          ) : suggestions.length === 0 ? (
            <p className="mt-2 text-xs text-gray-500">未发现建议关联</p>
          ) : (
            <ul className="mt-2 space-y-2">
              {suggestions.map((s) => (
                <li
                  key={s.target_doc_id}
                  className="flex items-center justify-between rounded bg-white p-2"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500">
                        {RELATION_LABELS[s.relation_type] || s.relation_type}
                      </span>
                      <span className="truncate text-sm text-gray-700">
                        {s.target_title}
                      </span>
                      <span className="text-xs text-gray-400">
                        {Math.round(s.confidence * 100)}%
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-gray-400">{s.reason}</p>
                  </div>
                  <button
                    onClick={() => handleAcceptSuggestion(s)}
                    className="ml-2 shrink-0 rounded bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700"
                  >
                    确认
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-gray-900">添加关联</h3>

            {/* Search */}
            <div className="mt-4">
              <label className="text-sm text-gray-600">搜索目标文档</label>
              <div className="mt-1 flex gap-2">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  placeholder="输入文档标题..."
                  className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                />
                <button
                  onClick={handleSearch}
                  disabled={searching}
                  className="rounded-lg bg-gray-100 px-3 py-2 text-sm text-gray-700 hover:bg-gray-200 disabled:opacity-50"
                >
                  {searching ? "..." : "搜索"}
                </button>
              </div>
              {searchResults.length > 0 && (
                <ul className="mt-2 max-h-40 overflow-y-auto rounded-lg border border-gray-200">
                  {searchResults.map((d) => (
                    <li
                      key={d.id}
                      onClick={() => {
                        setSelectedDoc(d);
                        setSearchResults([]);
                      }}
                      className={`cursor-pointer px-3 py-2 text-sm hover:bg-gray-50 ${
                        selectedDoc?.id === d.id
                          ? "bg-blue-50 text-blue-700"
                          : "text-gray-700"
                      }`}
                    >
                      {d.title}
                    </li>
                  ))}
                </ul>
              )}
              {selectedDoc && (
                <div className="mt-2 flex items-center gap-2 rounded bg-blue-50 px-3 py-1.5 text-sm text-blue-700">
                  已选: {selectedDoc.title}
                  <button
                    onClick={() => setSelectedDoc(null)}
                    className="text-blue-400 hover:text-blue-600"
                  >
                    ×
                  </button>
                </div>
              )}
            </div>

            {/* Relation type */}
            <div className="mt-4">
              <label className="text-sm text-gray-600">关联类型</label>
              <select
                value={relationType}
                onChange={(e) => setRelationType(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              >
                {RELATION_OPTIONS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label} ({value})
                  </option>
                ))}
              </select>
            </div>

            {/* Note */}
            <div className="mt-4">
              <label className="text-sm text-gray-600">备注（可选）</label>
              <input
                type="text"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="关联说明..."
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>

            {/* Actions */}
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowAddModal(false);
                  setSelectedDoc(null);
                  setSearchQuery("");
                  setSearchResults([]);
                  setNote("");
                }}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={handleCreate}
                disabled={!selectedDoc || creating}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {creating ? "创建中..." : "确认创建"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
