"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";
import KnowledgeGraph from "@/components/wiki/knowledge-graph";

interface GraphData {
  nodes: Array<{ id: string; label: string; node_type: string; node_path: string[]; status: string }>;
  edges: Array<{ id: string; source: string; target: string; edge_type: string; relation_type?: string }>;
  node_count: number;
  edge_count: number;
}

export default function GraphPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [data, setData] = useState<GraphData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchGraph = async () => {
    setIsLoading(true);
    setError("");
    try {
      const resp = await api.get<GraphData>(`/v1/projects/${projectId}/graph`);
      setData(resp.data);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "加载知识图谱失败");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, [projectId]);

  if (isLoading) {
    return (
      <div className="flex h-[70vh] items-center justify-center">
        <div className="text-gray-400">加载知识图谱中...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex h-[70vh] flex-col items-center justify-center gap-3">
        <div className="text-red-500">{error || "加载失败"}</div>
        <button
          onClick={fetchGraph}
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
        >
          重试
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">知识图谱</h1>
        <Link
          href={`/projects/${projectId}`}
          className="text-sm text-primary-600 hover:underline"
        >
          返回项目
        </Link>
      </div>
      <div className="h-[75vh] rounded-xl border border-gray-200 bg-white shadow-sm">
        <KnowledgeGraph nodes={data.nodes} edges={data.edges} projectId={projectId} />
      </div>
    </div>
  );
}
