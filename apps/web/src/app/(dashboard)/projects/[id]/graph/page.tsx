"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";
import { usePermission } from "@/hooks/usePermission";
import KnowledgeGraph from "@/components/wiki/knowledge-graph";
import { NodeMergeModal } from "@/components/graph/NodeMergeModal";
import { NodeSplitPanel } from "@/components/graph/NodeSplitPanel";

interface GraphNode {
  id: string;
  label: string;
  node_type: string;
  node_path: string[];
  status: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: Array<{ id: string; source: string; target: string; edge_type: string; relation_type?: string }>;
  node_count: number;
  edge_count: number;
}

interface ArchNode {
  id: string;
  node_name: string;
  parent_id: string | null;
  level: number;
  status: string;
}

interface ArchCategory {
  nodeId: string;
  name: string;
  docCount: number;
}

export default function GraphPage() {
  const params = useParams();
  const projectId = params.id as string;
  const { hasRole } = usePermission();
  const isAdmin = hasRole("project_admin");

  const [data, setData] = useState<GraphData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // Edit state
  const [archNodes, setArchNodes] = useState<ArchNode[]>([]);
  const [selectedNodeIds, setSelectedNodeIds] = useState<Set<string>>(new Set());
  const [showMerge, setShowMerge] = useState(false);
  const [splitTarget, setSplitTarget] = useState<ArchCategory | null>(null);

  const fetchGraph = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const resp = await api.get<GraphData>(`/v1/projects/${projectId}/graph`);
      setData(resp.data);

      // Also fetch architecture nodes for the category panel
      if (isAdmin) {
        try {
          const archResp = await api.get<{ id: string; name: string }[]>(
            `/v1/projects/${projectId}/architectures`,
          );
          const archs = archResp.data ?? [];
          if (archs.length > 0) {
            const nodesResp = await api.get<ArchNode[]>(
              `/v1/architectures/${archs[0].id}/nodes`,
            );
            setArchNodes((nodesResp.data ?? []).filter((n) => n.status !== "archived"));
          }
        } catch {
          // Non-critical — panel just won't show
        }
      }
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "加载知识图谱失败");
    } finally {
      setIsLoading(false);
    }
  }, [projectId, isAdmin]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  // Build categories from arch nodes + doc count from graph data
  const categories: ArchCategory[] = (() => {
    if (!data || archNodes.length === 0) return [];
    // Count docs per node_path leaf name
    const docCountByName = new Map<string, number>();
    for (const n of data.nodes) {
      if (n.node_path.length === 0) continue;
      const leaf = n.node_path[n.node_path.length - 1];
      docCountByName.set(leaf, (docCountByName.get(leaf) ?? 0) + 1);
    }
    return archNodes.map((an) => ({
      nodeId: an.id,
      name: an.node_name,
      docCount: docCountByName.get(an.node_name) ?? 0,
    }));
  })();

  const toggleCategory = (nodeId: string) => {
    setSelectedNodeIds((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  };

  const handleMergeSuccess = () => {
    setShowMerge(false);
    setSelectedNodeIds(new Set());
    fetchGraph();
  };

  const handleSplitSuccess = () => {
    setSplitTarget(null);
    fetchGraph();
  };

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

      <div className="flex gap-4">
        {/* Graph */}
        <div className="h-[75vh] flex-1 rounded-xl border border-gray-200 bg-white shadow-sm">
          <KnowledgeGraph nodes={data.nodes} edges={data.edges} projectId={projectId} />
        </div>

        {/* Category management panel (admin only) */}
        {isAdmin && categories.length > 0 && (
          <div className="h-[75vh] w-64 overflow-y-auto rounded-xl border border-gray-200 bg-white p-3 shadow-sm">
            <h3 className="mb-2 text-sm font-semibold text-gray-900">分类管理</h3>
            <p className="mb-3 text-xs text-gray-400">勾选分类后可合并，或点击拆分</p>

            <div className="space-y-1.5">
              {categories.map((cat) => (
                <div
                  key={cat.nodeId}
                  className={`flex items-center justify-between rounded-lg px-2 py-1.5 text-sm ${
                    selectedNodeIds.has(cat.nodeId)
                      ? "bg-primary-50 ring-1 ring-primary-300"
                      : "hover:bg-gray-50"
                  }`}
                >
                  <label className="flex flex-1 cursor-pointer items-center gap-2">
                    <input
                      type="checkbox"
                      checked={selectedNodeIds.has(cat.nodeId)}
                      onChange={() => toggleCategory(cat.nodeId)}
                      className="h-3.5 w-3.5 rounded border-gray-300 text-primary-600"
                    />
                    <span className="truncate text-gray-700" title={cat.name}>
                      {cat.name}
                    </span>
                    <span className="text-xs text-gray-400">{cat.docCount}</span>
                  </label>
                  <button
                    onClick={() => setSplitTarget(cat)}
                    className="ml-1 shrink-0 text-xs text-gray-400 hover:text-primary-600"
                    title="拆分此分类"
                  >
                    拆分
                  </button>
                </div>
              ))}
            </div>

            {selectedNodeIds.size >= 2 && (
              <button
                onClick={() => setShowMerge(true)}
                className="mt-3 w-full rounded-lg bg-primary-600 px-3 py-2 text-sm font-medium text-white hover:bg-primary-700"
              >
                合并选中 ({selectedNodeIds.size})
              </button>
            )}
          </div>
        )}
      </div>

      {/* Merge Modal */}
      {showMerge && (
        <NodeMergeModal
          projectId={projectId}
          selectedNodes={categories
            .filter((c) => selectedNodeIds.has(c.nodeId))
            .map((c) => ({ id: c.nodeId, name: c.name }))}
          onClose={() => setShowMerge(false)}
          onSuccess={handleMergeSuccess}
        />
      )}

      {/* Split Panel */}
      {splitTarget && (
        <NodeSplitPanel
          projectId={projectId}
          nodeId={splitTarget.nodeId}
          nodeName={splitTarget.name}
          onClose={() => setSplitTarget(null)}
          onSuccess={handleSplitSuccess}
        />
      )}
    </div>
  );
}
