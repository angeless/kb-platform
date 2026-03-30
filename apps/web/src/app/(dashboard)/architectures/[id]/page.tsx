"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, ApiClientError } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";
import { PermissionGuard } from "@/components/PermissionGuard";
import { TreeNode, buildTree, type TreeNodeData } from "@/components/tree-node";
import { NodePanel } from "@/components/node-panel";

interface Architecture {
  id: string;
  name: string;
  version: string;
  status: string;
  project_id: string;
}

export default function ArchitectureDetailPage() {
  const params = useParams();
  const archId = params.id as string;

  const [arch, setArch] = useState<Architecture | null>(null);
  const [tree, setTree] = useState<TreeNodeData[]>([]);
  const [selectedNode, setSelectedNode] = useState<TreeNodeData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // Add node form
  const [showAddForm, setShowAddForm] = useState(false);
  const [newNodeName, setNewNodeName] = useState("");
  const [newNodeType, setNewNodeType] = useState("category");
  const [adding, setAdding] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [archResp, nodesResp] = await Promise.all([
        api.get<Architecture>(`/v1/architectures/${archId}`),
        api.get<TreeNodeData[]>(`/v1/architectures/${archId}/nodes`),
      ]);
      setArch(archResp.data);
      setTree(buildTree(nodesResp.data));
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }, [archId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAddNode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNodeName.trim()) return;
    setAdding(true);
    try {
      await api.post(`/v1/architectures/${archId}/nodes`, {
        node_name: newNodeName.trim(),
        node_type: newNodeType,
        level: selectedNode ? selectedNode.level + 1 : 0,
        parent_id: selectedNode?.id || null,
      });
      setNewNodeName("");
      setShowAddForm(false);
      await fetchData();
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "添加失败");
    } finally {
      setAdding(false);
    }
  };

  const handlePublish = async () => {
    try {
      await api.post(`/v1/architectures/${archId}/publish`, {});
      await fetchData();
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "发布失败");
    }
  };

  if (isLoading) return <div className="py-12 text-center text-gray-400">加载中...</div>;
  if (error || !arch) return <div className="py-12 text-center text-red-500">{error}</div>;

  return (
    <div className="flex h-[calc(100vh-100px)]">
      {/* Left: Tree */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-5 py-4">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-gray-900">{arch.name}</h1>
            <StatusBadge status={arch.status} />
            <span className="text-sm text-gray-400">v{arch.version}</span>
          </div>
          <div className="flex gap-2">
            <PermissionGuard action="edit">
              <button
                onClick={() => setShowAddForm(!showAddForm)}
                className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
              >
                + 新增节点
              </button>
            </PermissionGuard>
            {arch.status === "draft" && (
              <PermissionGuard action="edit">
                <button
                  onClick={handlePublish}
                  className="rounded-lg bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700"
                >
                  发布架构
                </button>
              </PermissionGuard>
            )}
          </div>
        </div>

        {/* Add Node Form */}
        {showAddForm && (
          <form onSubmit={handleAddNode} className="border-b border-gray-200 bg-gray-50 px-5 py-3">
            <div className="flex items-end gap-3">
              <div className="flex-1">
                <label className="mb-1 block text-xs text-gray-500">
                  节点名称 {selectedNode && `（父节点：${selectedNode.node_name}）`}
                </label>
                <input
                  type="text"
                  value={newNodeName}
                  onChange={(e) => setNewNodeName(e.target.value)}
                  placeholder="输入节点名称"
                  className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-primary-500 focus:outline-none"
                />
              </div>
              <select
                value={newNodeType}
                onChange={(e) => setNewNodeType(e.target.value)}
                className="rounded border border-gray-300 px-2 py-1.5 text-sm"
              >
                <option value="category">分类 category</option>
                <option value="topic">主题 topic</option>
                <option value="document">文档 document</option>
                <option value="glossary">术语 glossary</option>
                <option value="index">索引 index</option>
              </select>
              <button
                type="submit"
                disabled={adding}
                className="rounded-lg bg-primary-600 px-4 py-1.5 text-sm text-white hover:bg-primary-700 disabled:opacity-50"
              >
                {adding ? "添加中..." : "添加"}
              </button>
            </div>
          </form>
        )}

        {/* Tree */}
        <div className="flex-1 overflow-y-auto p-3">
          {tree.length === 0 ? (
            <div className="py-12 text-center text-gray-400">
              暂无节点，点击"新增节点"开始构建架构
            </div>
          ) : (
            tree.map((root) => (
              <TreeNode
                key={root.id}
                node={root}
                onSelect={setSelectedNode}
                selectedId={selectedNode?.id || null}
              />
            ))
          )}
        </div>
      </div>

      {/* Right: Node Panel */}
      {selectedNode && (
        <div className="w-80 flex-shrink-0">
          <NodePanel
            node={selectedNode}
            archId={archId}
            onClose={() => setSelectedNode(null)}
            onUpdated={fetchData}
          />
        </div>
      )}
    </div>
  );
}
