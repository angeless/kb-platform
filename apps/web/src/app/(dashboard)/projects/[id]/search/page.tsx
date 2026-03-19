"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

interface TextHit {
  doc_id: string;
  title: string;
  doc_type: string;
  status: string;
  snippet: string;
  matched_field: string;
  version: number;
}

interface SemanticHit {
  doc_id: string;
  title: string;
  doc_type: string;
  status: string;
  score: number;
}

type SearchMode = "text" | "semantic";

export default function SearchPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<SearchMode>("text");
  const [textResults, setTextResults] = useState<TextHit[]>([]);
  const [semanticResults, setSemanticResults] = useState<SemanticHit[]>([]);
  const [total, setTotal] = useState(0);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState("");

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    setError("");
    setSearched(true);

    try {
      if (mode === "text") {
        const resp = await api.post<TextHit[]>("/v1/search/text", {
          project_id: projectId,
          query: query.trim(),
        });
        setTextResults(resp.data);
        setTotal(resp.meta?.total ?? resp.data.length);
        setSemanticResults([]);
      } else {
        const resp = await api.post<SemanticHit[]>("/v1/search/semantic", {
          project_id: projectId,
          query: query.trim(),
          top_k: 20,
        });
        setSemanticResults(resp.data);
        setTotal(resp.data.length);
        setTextResults([]);
      }
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "搜索失败");
    } finally {
      setSearching(false);
    }
  };

  return (
    <div>
      <div className="mb-4">
        <Link href={`/projects/${projectId}`} className="text-sm text-primary-600 hover:underline">
          ← 返回项目
        </Link>
      </div>

      <h1 className="mb-6 text-2xl font-bold text-gray-900">知识检索</h1>

      {/* Mode Toggle */}
      <div className="mb-4 flex gap-1 border-b border-gray-200">
        <button
          onClick={() => setMode("text")}
          className={`border-b-2 px-4 py-2 text-sm ${mode === "text" ? "border-primary-600 font-medium text-primary-600" : "border-transparent text-gray-500"}`}
        >
          全文检索
        </button>
        <button
          onClick={() => setMode("semantic")}
          className={`border-b-2 px-4 py-2 text-sm ${mode === "semantic" ? "border-primary-600 font-medium text-primary-600" : "border-transparent text-gray-500"}`}
        >
          语义检索
        </button>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="mb-6 flex gap-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={mode === "text" ? "输入关键词..." : "输入自然语言描述..."}
          className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
        />
        <button
          type="submit"
          disabled={searching || !query.trim()}
          className="rounded-lg bg-primary-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          {searching ? "搜索中..." : "搜索"}
        </button>
      </form>

      {error && <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

      {/* Results */}
      {searched && (
        <div>
          <p className="mb-3 text-sm text-gray-500">
            找到 {total} 条结果
            {mode === "semantic" && " (按相似度排序)"}
          </p>

          {/* Text Results */}
          {mode === "text" && textResults.length > 0 && (
            <div className="space-y-3">
              {textResults.map((hit) => (
                <Link
                  key={hit.doc_id}
                  href={`/docs/${hit.doc_id}`}
                  className="block rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md"
                >
                  <div className="flex items-center gap-3">
                    <h3 className="font-semibold text-gray-900">{hit.title}</h3>
                    <StatusBadge status={hit.status} />
                    <span className="text-xs text-gray-400">{hit.doc_type} · v{hit.version}</span>
                  </div>
                  <p className="mt-2 text-sm text-gray-600">{hit.snippet}</p>
                  <span className="mt-1 text-xs text-gray-400">匹配字段：{hit.matched_field === "title" ? "标题" : "内容"}</span>
                </Link>
              ))}
            </div>
          )}

          {/* Semantic Results */}
          {mode === "semantic" && semanticResults.length > 0 && (
            <div className="space-y-3">
              {semanticResults.map((hit) => (
                <Link
                  key={hit.doc_id}
                  href={`/docs/${hit.doc_id}`}
                  className="block rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md"
                >
                  <div className="flex items-center gap-3">
                    <h3 className="font-semibold text-gray-900">{hit.title}</h3>
                    <StatusBadge status={hit.status} />
                    <span className="text-xs text-gray-400">{hit.doc_type}</span>
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    <div className="h-1.5 w-24 overflow-hidden rounded-full bg-gray-200">
                      <div
                        className="h-full rounded-full bg-primary-500"
                        style={{ width: `${Math.round(hit.score * 100)}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500">
                      相似度 {(hit.score * 100).toFixed(1)}%
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}

          {/* No Results */}
          {searched && total === 0 && !searching && (
            <div className="py-8 text-center text-gray-400">
              {mode === "semantic" ? "没有找到语义相关的文档，请先为文档生成 embedding" : "没有匹配的结果"}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
