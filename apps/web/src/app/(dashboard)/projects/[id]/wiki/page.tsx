"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";

interface ArchNode {
  id: string;
  node_name: string;
  node_type: string;
  level: number;
  description: string | null;
  parent_id: string | null;
}

interface DocSummary {
  id: string;
  title: string;
  doc_type: string;
  status: string;
}

interface Architecture {
  id: string;
  version: number;
  status: string;
}

export default function WikiHomePage() {
  const params = useParams();
  const projectId = params.id as string;

  const [nodes, setNodes] = useState<ArchNode[]>([]);
  const [recentDocs, setRecentDocs] = useState<DocSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const archResp = await api.get<Architecture[]>(
          `/v1/projects/${projectId}/architectures`,
        );
        const archs = archResp.data;
        const published = archs.find((a) => a.status === "published") || archs[0];

        if (published) {
          const nodesResp = await api.get<ArchNode[]>(
            `/v1/architectures/${published.id}/nodes`,
          );
          setNodes(nodesResp.data);
        }

        const docsResp = await api.get<DocSummary[]>(
          `/v1/docs?project_id=${projectId}&page=1&page_size=10`,
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

  const topNodes = nodes.filter((n) => !n.parent_id);

  return (
    <div className="mx-auto max-w-5xl px-4 py-6">
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">知识 Wiki</h1>
        <Link
          href={`/projects/${projectId}/wiki/search`}
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
        >
          搜索知识库
        </Link>
      </div>

      {topNodes.length > 0 && (
        <section className="mb-10">
          <h2 className="mb-4 text-lg font-semibold text-gray-800">架构概览</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {topNodes.map((node) => {
              const childCount = nodes.filter((n) => n.parent_id === node.id).length;
              return (
                <div key={node.id} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm hover:shadow-md">
                  <div className="mb-2 text-lg font-medium text-gray-900">{node.node_name}</div>
                  {node.description && <p className="mb-3 text-sm text-gray-500 line-clamp-2">{node.description}</p>}
                  <div className="text-xs text-gray-400">{childCount} 个子节点</div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      <section>
        <h2 className="mb-4 text-lg font-semibold text-gray-800">最近更新</h2>
        {recentDocs.length === 0 ? (
          <p className="text-sm text-gray-400">暂无文档</p>
        ) : (
          <ul className="divide-y divide-gray-100 rounded-xl border border-gray-200 bg-white">
            {recentDocs.map((doc) => (
              <li key={doc.id}>
                <Link href={`/projects/${projectId}/wiki/${doc.id}`} className="flex items-center justify-between px-4 py-3 hover:bg-gray-50">
                  <span className="text-sm font-medium text-gray-800">{doc.title}</span>
                  <span className="text-xs text-gray-400">{doc.doc_type}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
