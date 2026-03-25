"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";

interface SearchHit {
  doc_id: string;
  title: string;
  snippet: string;
  score: number;
}

export default function WikiSearchPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchHit[]>([]);
  const [searched, setSearched] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setIsLoading(true);
    setError("");
    try {
      const resp = await api.get<SearchHit[]>(
        `/v1/search/hybrid?project_id=${projectId}&query=${encodeURIComponent(query)}&page_size=20`,
      );
      setResults(resp.data);
      setSearched(true);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "搜索失败");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <div className="mb-6">
        <Link href={`/projects/${projectId}/wiki`} className="text-sm text-gray-500 hover:text-gray-700">
          ← 返回 Wiki
        </Link>
      </div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Wiki 搜索</h1>
      <form onSubmit={handleSearch} className="mb-8 flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="搜索知识库..."
          className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
        />
        <button
          type="submit"
          disabled={isLoading}
          className="rounded-lg bg-primary-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          {isLoading ? "搜索中..." : "搜索"}
        </button>
      </form>
      {error && <div className="mb-4 text-sm text-red-500">{error}</div>}
      {searched && results.length === 0 && (
        <p className="text-center text-sm text-gray-400">未找到相关结果</p>
      )}
      {results.length > 0 && (
        <ul className="divide-y divide-gray-100 rounded-xl border border-gray-200 bg-white">
          {results.map((hit) => (
            <li key={hit.doc_id}>
              <Link href={`/projects/${projectId}/wiki/${hit.doc_id}`} className="block px-4 py-3 hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-800">{hit.title}</span>
                  <span className="text-xs text-gray-400">{Math.round(hit.score * 100)}%</span>
                </div>
                {hit.snippet && <p className="mt-1 text-xs text-gray-500 line-clamp-2">{hit.snippet}</p>}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
