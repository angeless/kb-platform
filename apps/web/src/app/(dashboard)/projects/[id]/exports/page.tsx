"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";

interface Doc {
  id: string;
  title: string;
  doc_type: string;
  status: string;
}

type ExportFormat = "markdown" | "json";

export default function ExportPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [docs, setDocs] = useState<Doc[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [format, setFormat] = useState<ExportFormat>("markdown");
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetch = async () => {
      try {
        const resp = await api.get<Doc[]>(
          `/v1/docs?project_id=${projectId}&page_size=100`,
        );
        setDocs(resp.data);
      } catch (e) {
        setError(e instanceof ApiClientError ? e.message : "加载失败");
      } finally {
        setIsLoading(false);
      }
    };
    fetch();
  }, [projectId]);

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selected.size === docs.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(docs.map((d) => d.id)));
    }
  };

  const handleExport = async () => {
    if (selected.size === 0) return;
    setExporting(true);
    setError("");

    try {
      const resp = await api.post<{ content: string; filename: string }>("/v1/docs/export", {
        doc_ids: Array.from(selected),
        format,
      });
      // Trigger download
      const blob = new Blob([resp.data.content], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = resp.data.filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "导出失败");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div>
      <div className="mb-4">
        <Link href={`/projects/${projectId}`} className="text-sm text-primary-600 hover:underline">
          ← 返回项目
        </Link>
      </div>

      <h1 className="mb-6 text-2xl font-bold text-gray-900">文档导出</h1>

      {error && <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

      {/* Controls */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={selected.size === docs.length && docs.length > 0} onChange={selectAll} className="rounded" />
            全选 ({selected.size}/{docs.length})
          </label>
          <select
            value={format}
            onChange={(e) => setFormat(e.target.value as ExportFormat)}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
          >
            <option value="markdown">Markdown</option>
            <option value="json">JSON</option>
          </select>
        </div>
        <button
          onClick={handleExport}
          disabled={selected.size === 0 || exporting}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          {exporting ? "导出中..." : `导出 ${selected.size} 篇文档`}
        </button>
      </div>

      {/* Doc List */}
      {isLoading ? (
        <div className="py-12 text-center text-gray-400">加载中...</div>
      ) : docs.length === 0 ? (
        <div className="py-12 text-center text-gray-400">暂无文档可导出</div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          {docs.map((doc) => (
            <label
              key={doc.id}
              className="flex cursor-pointer items-center gap-3 border-b border-gray-100 px-5 py-3 last:border-0 hover:bg-gray-50"
            >
              <input
                type="checkbox"
                checked={selected.has(doc.id)}
                onChange={() => toggleSelect(doc.id)}
                className="rounded"
              />
              <div className="flex-1">
                <span className="font-medium text-gray-900">{doc.title}</span>
                <span className="ml-2 text-xs text-gray-400">{doc.doc_type}</span>
              </div>
              <span className={`text-xs ${doc.status === "published" ? "text-green-600" : "text-gray-400"}`}>
                {doc.status}
              </span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
