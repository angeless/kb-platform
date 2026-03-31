"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";
import { usePermission } from "@/hooks/usePermission";
import KnowledgeGraph from "@/components/wiki/knowledge-graph";
import { NodeMergeModal } from "@/components/graph/NodeMergeModal";
import { NodeSplitPanel } from "@/components/graph/NodeSplitPanel";
import { PermissionGuard } from "@/components/PermissionGuard";

interface GraphNode {
  id: string;
  label: string;
  node_type: string;
  node_path: string[];
  status: string;
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  edge_type: string;
  relation_type?: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  node_count: number;
  edge_count: number;
}

const RELATION_LABELS: Record<string, string> = {
  related: "相关",
  depends_on: "依赖",
  extends: "扩展",
  contradicts: "矛盾",
  supersedes: "替代",
};

interface EdgeDetail {
  edgeId: string;
  edge: GraphEdge;
  sourceLabel: string;
  targetLabel: string;
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

  // Edge detail popup
  const [edgeDetail, setEdgeDetail] = useState<EdgeDetail | null>(null);
  const [deletingEdge, setDeletingEdge] = useState(false);

  // Add cross-ref modal
  const [showAddCrossRef, setShowAddCrossRef] = useState(false);
  const [addSearchQuery, setAddSearchQuery] = useState("");
  const [addSearchResults, setAddSearchResults] = useState<Array<{ id: string; title: string }>>([]);
  const [addSearching, setAddSearching] = useState(false);
  const [addSelectedSource, setAddSelectedSource] = useState<{ id: string; title: string } | null>(null);
  const [addSelectedTarget, setAddSelectedTarget] = useState<{ id: string; title: string } | null>(null);
  const [addRelationType, setAddRelationType] = useState("related");
  const [addNote, setAddNote] = useState("");
  const [addCreating, setAddCreating] = useState(false);
  const [actionMsg, setActionMsg] = useState("");

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

  const handleEdgeClick = useCallback(
    (edgeId: string, edge: GraphEdge) => {
      if (!data) return;
      const sourceNode = data.nodes.find((n) => n.id === edge.source);
      const targetNode = data.nodes.find((n) => n.id === edge.target);
      setEdgeDetail({
        edgeId,
        edge,
        sourceLabel: sourceNode?.label ?? edge.source.slice(0, 8),
        targetLabel: targetNode?.label ?? edge.target.slice(0, 8),
      });
    },
    [data],
  );

  const handleDeleteEdge = async () => {
    if (!edgeDetail) return;
    setDeletingEdge(true);
    try {
      await api.del(`/v1/cross-refs/${edgeDetail.edgeId}`);
      setEdgeDetail(null);
      fetchGraph();
    } catch (e) {
      setActionMsg(e instanceof ApiClientError ? e.message : "删除失败");
    } finally {
      setDeletingEdge(false);
    }
  };

  const handleAddSearch = async () => {
    if (!addSearchQuery.trim() || !data) return;
    setAddSearching(true);
    try {
      // Use graph nodes as search source (they're already loaded)
      const q = addSearchQuery.toLowerCase();
      const filtered = data.nodes
        .filter((n) => n.label.toLowerCase().includes(q))
        .map((n) => ({ id: n.id, title: n.label }));
      setAddSearchResults(filtered.slice(0, 10));
    } finally {
      setAddSearching(false);
    }
  };

  const handleAddCreate = async () => {
    if (!addSelectedSource || !addSelectedTarget) return;
    setAddCreating(true);
    setActionMsg("");
    try {
      await api.post("/v1/cross-refs", {
        source_doc_id: addSelectedSource.id,
        target_doc_id: addSelectedTarget.id,
        relation_type: addRelationType,
        confidence: 1.0,
        note: addNote || null,
      });
      setShowAddCrossRef(false);
      setAddSelectedSource(null);
      setAddSelectedTarget(null);
      setAddSearchQuery("");
      setAddSearchResults([]);
      setAddNote("");
      setAddRelationType("related");
      fetchGraph();
    } catch (e) {
      setActionMsg(e instanceof ApiClientError ? e.message : "创建失败");
    } finally {
      setAddCreating(false);
    }
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
        <div className="flex items-center gap-3">
          <PermissionGuard action="edit">
            <button
              onClick={() => setShowAddCrossRef(true)}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              添加关联
            </button>
          </PermissionGuard>
          <Link
            href={`/projects/${projectId}`}
            className="text-sm text-primary-600 hover:underline"
          >
            返回项目
          </Link>
        </div>
      </div>

      {actionMsg && (
        <div className="mb-3 rounded-lg bg-red-50 p-3 text-sm text-red-600">
          {actionMsg}
        </div>
      )}

      <div className="flex gap-4">
        {/* Graph */}
        <div className="h-[75vh] flex-1 rounded-xl border border-gray-200 bg-white shadow-sm">
          <KnowledgeGraph nodes={data.nodes} edges={data.edges} projectId={projectId} onEdgeClick={handleEdgeClick} />
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

      {/* Edge Detail Popup */}
      {edgeDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-gray-900">关联详情</h3>
            <div className="mt-4 space-y-3">
              <div>
                <span className="text-xs text-gray-400">来源文档</span>
                <p className="text-sm text-gray-700">{edgeDetail.sourceLabel}</p>
              </div>
              <div>
                <span className="text-xs text-gray-400">目标文档</span>
                <p className="text-sm text-gray-700">{edgeDetail.targetLabel}</p>
              </div>
              <div>
                <span className="text-xs text-gray-400">关联类型</span>
                <p className="text-sm text-gray-700">
                  <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs">
                    {RELATION_LABELS[edgeDetail.edge.relation_type ?? ""] ?? edgeDetail.edge.relation_type ?? "未知"}
                  </span>
                </p>
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setEdgeDetail(null)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                关闭
              </button>
              <PermissionGuard action="edit">
                <button
                  onClick={handleDeleteEdge}
                  disabled={deletingEdge}
                  className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                >
                  {deletingEdge ? "删除中..." : "删除关联"}
                </button>
              </PermissionGuard>
            </div>
          </div>
        </div>
      )}

      {/* Add Cross-Ref Modal */}
      {showAddCrossRef && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-gray-900">添加关联</h3>

            {/* Source doc */}
            <div className="mt-4">
              <label className="text-sm text-gray-600">来源文档</label>
              {addSelectedSource ? (
                <div className="mt-1 flex items-center gap-2 rounded bg-blue-50 px-3 py-1.5 text-sm text-blue-700">
                  {addSelectedSource.title}
                  <button onClick={() => setAddSelectedSource(null)} className="text-blue-400 hover:text-blue-600">×</button>
                </div>
              ) : (
                <div className="mt-1">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={!addSelectedSource ? addSearchQuery : ""}
                      onChange={(e) => setAddSearchQuery(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleAddSearch()}
                      placeholder="搜索文档标题..."
                      className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                    />
                    <button onClick={handleAddSearch} disabled={addSearching} className="rounded-lg bg-gray-100 px-3 py-2 text-sm text-gray-700 hover:bg-gray-200 disabled:opacity-50">
                      {addSearching ? "..." : "搜索"}
                    </button>
                  </div>
                  {addSearchResults.length > 0 && !addSelectedSource && (
                    <ul className="mt-2 max-h-32 overflow-y-auto rounded-lg border border-gray-200">
                      {addSearchResults.map((d) => (
                        <li key={d.id} onClick={() => { setAddSelectedSource(d); setAddSearchResults([]); setAddSearchQuery(""); }}
                          className="cursor-pointer px-3 py-2 text-sm text-gray-700 hover:bg-gray-50">
                          {d.title}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>

            {/* Target doc */}
            <div className="mt-4">
              <label className="text-sm text-gray-600">目标文档</label>
              {addSelectedTarget ? (
                <div className="mt-1 flex items-center gap-2 rounded bg-blue-50 px-3 py-1.5 text-sm text-blue-700">
                  {addSelectedTarget.title}
                  <button onClick={() => setAddSelectedTarget(null)} className="text-blue-400 hover:text-blue-600">×</button>
                </div>
              ) : (
                <div className="mt-1">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={!addSelectedTarget ? addSearchQuery : ""}
                      onChange={(e) => setAddSearchQuery(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleAddSearch()}
                      placeholder="搜索文档标题..."
                      className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                    />
                    <button onClick={handleAddSearch} disabled={addSearching} className="rounded-lg bg-gray-100 px-3 py-2 text-sm text-gray-700 hover:bg-gray-200 disabled:opacity-50">
                      {addSearching ? "..." : "搜索"}
                    </button>
                  </div>
                  {addSearchResults.length > 0 && !addSelectedTarget && (
                    <ul className="mt-2 max-h-32 overflow-y-auto rounded-lg border border-gray-200">
                      {addSearchResults.map((d) => (
                        <li key={d.id} onClick={() => { setAddSelectedTarget(d); setAddSearchResults([]); setAddSearchQuery(""); }}
                          className="cursor-pointer px-3 py-2 text-sm text-gray-700 hover:bg-gray-50">
                          {d.title}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>

            {/* Relation type */}
            <div className="mt-4">
              <label className="text-sm text-gray-600">关联类型</label>
              <select value={addRelationType} onChange={(e) => setAddRelationType(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none">
                {Object.entries(RELATION_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label} ({value})</option>
                ))}
              </select>
            </div>

            {/* Note */}
            <div className="mt-4">
              <label className="text-sm text-gray-600">备注（可选）</label>
              <input type="text" value={addNote} onChange={(e) => setAddNote(e.target.value)} placeholder="关联说明..."
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button onClick={() => { setShowAddCrossRef(false); setAddSelectedSource(null); setAddSelectedTarget(null); setAddSearchQuery(""); setAddSearchResults([]); setAddNote(""); }}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
                取消
              </button>
              <button onClick={handleAddCreate} disabled={!addSelectedSource || !addSelectedTarget || addCreating}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                {addCreating ? "创建中..." : "确认创建"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
