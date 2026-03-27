"use client";

import Link from "next/link";

interface ArchNode {
  id: string;
  node_name: string;
  parent_id: string | null;
}

interface WikiBreadcrumbProps {
  nodes: ArchNode[];
  nodeId: string | null;
  projectId: string;
}

function buildPath(nodes: ArchNode[], nodeId: string): ArchNode[] {
  const map = new Map(nodes.map((n) => [n.id, n]));
  const path: ArchNode[] = [];
  let current = map.get(nodeId);
  while (current) {
    path.unshift(current);
    current = current.parent_id ? map.get(current.parent_id) : undefined;
  }
  return path;
}

export function WikiBreadcrumb({ nodes, nodeId, projectId }: WikiBreadcrumbProps) {
  const path = nodeId ? buildPath(nodes, nodeId) : [];

  return (
    <nav className="mb-4 flex items-center gap-1.5 text-sm text-gray-500">
      <Link href={`/projects/${projectId}/wiki`} className="hover:text-primary-600">
        Wiki
      </Link>
      {path.map((node) => (
        <span key={node.id} className="flex items-center gap-1.5">
          <span className="text-gray-300">/</span>
          <span className="text-gray-600">{node.node_name}</span>
        </span>
      ))}
    </nav>
  );
}
