"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";

interface DocSummary {
  id: string;
  title: string;
  doc_type: string;
  status: string;
}

export default function WikiHomePage() {
  const params = useParams();
  const projectId = params.id as string;

  const [recentDocs, setRecentDocs] = useState<DocSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const docsResp = await api.get<DocSummary[]>(
          `/v1/docs?project_id=${projectId}&page=1&page_size=20`,
        );
        setRecentDocs(docsResp.data);
      } catch (e) {
        setError(e instanceof ApiClientError ? e.message : "加载失败");
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [projectId]);

  if (isLoading) return <div className="py-12 text-center text-gray-400">加载中...</div>;
  if (error) return <div className="py-12 text-center text-red-500">{error}</div>;

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <h1 className="mb-2 text-2xl font-bold text-gray-900">知识 Wiki</h1>
      <p className="mb-8 text-sm text-gray-500">
        在左侧导航树中浏览架构，或使用侧栏搜索框快速查找文档。
      </p>

      <section>
        <h2 className="mb-4 text-lg font-semibold text-gray-800">最近文档</h2>
        {recentDocs.length === 0 ? (
          <p className="text-sm text-gray-400">暂无文档。上传资料并运行流水线后，文档将自动生成。</p>
        ) : (
          <ul className="divide-y divide-gray-100 rounded-xl border border-gray-200 bg-white shadow-sm">
            {recentDocs.map((doc) => (
              <li key={doc.id}>
                <Link
                  href={`/projects/${projectId}/wiki/${doc.id}`}
                  className="flex items-center justify-between px-5 py-3.5 hover:bg-gray-50"
                >
                  <div>
                    <span className="text-sm font-medium text-gray-800">{doc.title}</span>
                    <span className="ml-3 text-xs text-gray-400">{doc.doc_type}</span>
                  </div>
                  <span className={`rounded-full px-2 py-0.5 text-xs ${
                    doc.status === "published" ? "bg-green-50 text-green-600" :
                    doc.status === "reviewing" ? "bg-yellow-50 text-yellow-600" :
                    "bg-gray-50 text-gray-500"
                  }`}>
                    {doc.status === "published" ? "已发布" : doc.status === "reviewing" ? "审核中" : "草稿"}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
