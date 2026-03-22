"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

const DOC_TYPE_LABELS: Record<string, string> = {
  topic: "主题", glossary: "术语", procedure: "流程", reference: "参考",
  concept: "概念", tutorial: "教程", faq: "常见问题",
};

interface TextHit {
  doc_id: string;
  title: string;
  doc_type: string;
  status: string;
  snippet: string;
  matched_field: string;
  version: number;
}

interface HybridHit {
  doc_id: string;
  title: string;
  doc_type: string;
  status: string;
  snippet: string;
  score: number;
  match_type: string;
}

interface QAAnswer {
  answer: string;
  sources: { doc_id: string; title: string; snippet: string; relevance: number }[];
  related_questions: string[];
}

type SearchMode = "hybrid" | "text" | "qa";

const MATCH_TYPE_LABELS: Record<string, { label: string; color: string }> = {
  keyword: { label: "关键词匹配", color: "bg-blue-100 text-blue-700" },
  semantic: { label: "语义匹配", color: "bg-purple-100 text-purple-700" },
  "keyword+semantic": { label: "双重匹配", color: "bg-green-100 text-green-700" },
};

export default function SearchPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<SearchMode>("hybrid");
  const [textResults, setTextResults] = useState<TextHit[]>([]);
  const [hybridResults, setHybridResults] = useState<HybridHit[]>([]);
  const [qaAnswer, setQaAnswer] = useState<QAAnswer | null>(null);
  const [total, setTotal] = useState(0);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState("");

  const handleSearch = async (e?: React.FormEvent, overrideQuery?: string) => {
    if (e) e.preventDefault();
    const q = (overrideQuery || query).trim();
    if (!q) return;
    if (overrideQuery) setQuery(overrideQuery);

    setSearching(true);
    setError("");
    setSearched(true);

    try {
      if (mode === "hybrid") {
        const resp = await api.post<HybridHit[]>("/v1/search/hybrid", {
          project_id: projectId, query: q,
        });
        setHybridResults(resp.data);
        setTotal(resp.meta?.total ?? resp.data.length);
        setTextResults([]);
        setQaAnswer(null);
      } else if (mode === "text") {
        const resp = await api.post<TextHit[]>("/v1/search/text", {
          project_id: projectId, query: q,
        });
        setTextResults(resp.data);
        setTotal(resp.meta?.total ?? resp.data.length);
        setHybridResults([]);
        setQaAnswer(null);
      } else {
        const resp = await api.post<QAAnswer>("/v1/qa/ask", {
          project_id: projectId, question: q, top_k: 5,
        });
        setQaAnswer(resp.data);
        setTotal(resp.data.sources.length);
        setTextResults([]);
        setHybridResults([]);
      }
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "搜索失败");
    } finally {
      setSearching(false);
    }
  };

  const handleRelatedQuestion = (q: string) => {
    setMode("qa");
    handleSearch(undefined, q);
  };

  return (
    <div>
      <div className="mb-4">
        <Link href={`/projects/${projectId}`} className="text-sm text-primary-600 hover:underline">
          &larr; 返回项目
        </Link>
      </div>

      <h1 className="mb-6 text-2xl font-bold text-gray-900">知识检索</h1>

      {/* Mode Tabs */}
      <div className="mb-4 flex gap-1 border-b border-gray-200">
        {([
          ["hybrid", "智能搜索"],
          ["text", "关键词搜索"],
          ["qa", "AI 问答"],
        ] as [SearchMode, string][]).map(([m, label]) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`border-b-2 px-4 py-2 text-sm ${mode === m ? "border-primary-600 font-medium text-primary-600" : "border-transparent text-gray-500"}`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="mb-6 flex gap-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={
            mode === "qa" ? "输入您的问题..." : mode === "hybrid" ? "输入关键词或问题..." : "输入关键词..."
          }
          className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
        />
        <button
          type="submit"
          disabled={searching || !query.trim()}
          className="rounded-lg bg-primary-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          {searching ? "搜索中..." : mode === "qa" ? "提问" : "搜索"}
        </button>
      </form>

      {error && <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

      {/* Results */}
      {searched && (
        <div>
          {/* QA Answer */}
          {mode === "qa" && qaAnswer && (
            <div className="space-y-4">
              <div className="rounded-xl border border-primary-200 bg-primary-50 p-6">
                <h3 className="mb-3 text-sm font-medium text-primary-700">AI 回答</h3>
                <div className="prose prose-sm max-w-none text-gray-800 whitespace-pre-wrap">
                  {qaAnswer.answer}
                </div>
              </div>

              {qaAnswer.sources.length > 0 && (
                <details className="rounded-xl border border-gray-200 bg-white">
                  <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-gray-700">
                    参考来源 ({qaAnswer.sources.length} 篇文档)
                  </summary>
                  <div className="space-y-2 px-4 pb-4">
                    {qaAnswer.sources.map((src) => (
                      <Link
                        key={src.doc_id}
                        href={`/docs/${src.doc_id}`}
                        className="block rounded-lg bg-gray-50 p-3 text-sm hover:bg-gray-100"
                      >
                        <span className="font-medium text-gray-900">{src.title}</span>
                        <span className="ml-2 text-xs text-gray-400">
                          相关度 {(src.relevance * 100).toFixed(0)}%
                        </span>
                      </Link>
                    ))}
                  </div>
                </details>
              )}

              {qaAnswer.related_questions.length > 0 && (
                <div className="rounded-xl border border-gray-200 bg-white p-4">
                  <h4 className="mb-2 text-sm font-medium text-gray-700">你可能还想了解</h4>
                  <div className="flex flex-wrap gap-2">
                    {qaAnswer.related_questions.map((q, i) => (
                      <button
                        key={i}
                        onClick={() => handleRelatedQuestion(q)}
                        className="rounded-lg bg-gray-100 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-200"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Hybrid Results */}
          {mode === "hybrid" && (
            <>
              <p className="mb-3 text-sm text-gray-500">找到 {total} 条结果</p>
              <div className="space-y-3">
                {hybridResults.map((hit) => {
                  const matchInfo = MATCH_TYPE_LABELS[hit.match_type] || MATCH_TYPE_LABELS["keyword"];
                  return (
                    <Link
                      key={hit.doc_id}
                      href={`/docs/${hit.doc_id}`}
                      className="block rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md"
                    >
                      <div className="flex items-center gap-3">
                        <h3 className="font-semibold text-gray-900">{hit.title}</h3>
                        <StatusBadge status={hit.status} />
                        <span className="text-xs text-gray-400">
                          {DOC_TYPE_LABELS[hit.doc_type] || hit.doc_type}
                        </span>
                        <span className={`rounded-full px-2 py-0.5 text-xs ${matchInfo.color}`}>
                          {matchInfo.label}
                        </span>
                      </div>
                      {hit.snippet && (
                        <p
                          className="mt-2 text-sm text-gray-600 [&_mark]:rounded-sm [&_mark]:bg-yellow-200 [&_mark]:px-0.5"
                          dangerouslySetInnerHTML={{ __html: hit.snippet }}
                        />
                      )}
                    </Link>
                  );
                })}
              </div>
            </>
          )}

          {/* Text Results */}
          {mode === "text" && textResults.length > 0 && (
            <>
              <p className="mb-3 text-sm text-gray-500">找到 {total} 条结果</p>
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
                      <span className="text-xs text-gray-400">
                        {DOC_TYPE_LABELS[hit.doc_type] || hit.doc_type} · v{hit.version}
                      </span>
                    </div>
                    <p
                      className="mt-2 text-sm text-gray-600 [&_mark]:rounded-sm [&_mark]:bg-yellow-200 [&_mark]:px-0.5"
                      dangerouslySetInnerHTML={{ __html: hit.snippet }}
                    />
                    <span className="mt-1 text-xs text-gray-400">
                      匹配字段：{hit.matched_field === "title" ? "标题" : "内容"}
                    </span>
                  </Link>
                ))}
              </div>
            </>
          )}

          {/* No Results */}
          {searched && total === 0 && !searching && (
            <div className="py-8 text-center text-gray-400">
              {mode === "qa" ? "AI 暂时无法回答，请换个问法试试" : "没有找到匹配的结果"}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
