"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { TreeNode, TreeNodeData, buildTree } from "@/components/tree-node";

interface WikiSidebarProps {
  projectId: string;
  selectedDocId?: string;
}

export function WikiSidebar({ projectId, selectedDocId }: WikiSidebarProps) {
  const [tree, setTree] = useState<TreeNodeData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const archResp = await api.get<{ id: string; status: string }[]>(
          `/v1/projects/${projectId}/architectures`,
        );
        const archs = archResp.data;
        const published = archs.find((a) => a.status === "published") || archs[0];
        if (published) {
          const nodesResp = await api.get<TreeNodeData[]>(
            `/v1/architectures/${published.id}/nodes`,
          );
          setTree(buildTree(nodesResp.data));
        }
      } catch {
        // Sidebar data is non-critical
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [projectId]);

  const handleNodeSelect = (node: TreeNodeData) => {
    setSelectedNodeId(node.id);
  };

  if (isLoading) {
    return <div className="p-4 text-xs text-gray-400">加载架构...</div>;
  }

  if (tree.length === 0) {
    return (
      <div className="p-4 text-xs text-gray-400">
        暂无架构树。
        <Link href={`/projects/${projectId}/architectures`} className="text-primary-600 hover:underline">
          去创建
        </Link>
      </div>
    );
  }

  return (
    <nav className="h-full overflow-y-auto border-r border-gray-200 bg-white p-2">
      <div className="mb-3 px-3 pt-2">
        <Link
          href={`/projects/${projectId}/wiki`}
          className="text-sm font-semibold text-gray-800 hover:text-primary-600"
        >
          知识 Wiki
        </Link>
      </div>
      {tree.map((node) => (
        <TreeNode
          key={node.id}
          node={node}
          onSelect={handleNodeSelect}
          selectedId={selectedNodeId}
        />
      ))}
    </nav>
  );
}
