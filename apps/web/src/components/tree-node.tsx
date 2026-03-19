"use client";

import { useState } from "react";
import { StatusBadge } from "@/components/status-badge";

export interface TreeNodeData {
  id: string;
  node_name: string;
  node_type: string;
  level: number;
  description: string | null;
  status: string;
  parent_id: string | null;
  children: TreeNodeData[];
}

interface TreeNodeProps {
  node: TreeNodeData;
  onSelect: (node: TreeNodeData) => void;
  selectedId: string | null;
}

const typeIcons: Record<string, string> = {
  category: "📁",
  topic: "📄",
  document: "📝",
  glossary: "📖",
  conflict: "⚠️",
  index: "📋",
};

export function TreeNode({ node, onSelect, selectedId }: TreeNodeProps) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = node.children.length > 0;

  return (
    <div>
      <div
        onClick={() => onSelect(node)}
        className={`flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${
          selectedId === node.id
            ? "bg-primary-50 text-primary-700"
            : "hover:bg-gray-50"
        }`}
        style={{ paddingLeft: `${node.level * 20 + 12}px` }}
      >
        {hasChildren ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setExpanded(!expanded);
            }}
            className="flex h-4 w-4 items-center justify-center text-gray-400"
          >
            {expanded ? "▾" : "▸"}
          </button>
        ) : (
          <span className="h-4 w-4" />
        )}
        <span>{typeIcons[node.node_type] || "📄"}</span>
        <span className="flex-1 truncate font-medium text-gray-800">
          {node.node_name}
        </span>
        <StatusBadge status={node.status} />
      </div>

      {expanded && hasChildren && (
        <div>
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              onSelect={onSelect}
              selectedId={selectedId}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/** Build tree from flat node list. */
export function buildTree(nodes: TreeNodeData[]): TreeNodeData[] {
  const map = new Map<string, TreeNodeData>();
  const roots: TreeNodeData[] = [];

  // First pass: create map entries with empty children
  for (const node of nodes) {
    map.set(node.id, { ...node, children: [] });
  }

  // Second pass: attach children to parents
  for (const node of nodes) {
    const current = map.get(node.id)!;
    if (node.parent_id && map.has(node.parent_id)) {
      map.get(node.parent_id)!.children.push(current);
    } else {
      roots.push(current);
    }
  }

  return roots;
}
