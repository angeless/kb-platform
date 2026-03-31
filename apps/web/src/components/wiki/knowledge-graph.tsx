"use client";

import { useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

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

interface KnowledgeGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  projectId: string;
  onEdgeClick?: (edgeId: string, edgeData: GraphEdge) => void;
}

const DEPTH_COLORS = ["#1e40af", "#3b82f6", "#60a5fa", "#93c5fd", "#bfdbfe"];

const RELATION_LABELS: Record<string, string> = {
  related: "相关",
  depends_on: "依赖",
  extends: "扩展",
  contradicts: "矛盾",
  supersedes: "替代",
};

export default function KnowledgeGraph({ nodes, edges, projectId, onEdgeClick }: KnowledgeGraphProps) {
  const router = useRouter();

  const flowNodes: Node[] = useMemo(() => {
    // Group nodes by depth for grid layout
    const byDepth = new Map<number, GraphNode[]>();
    for (const n of nodes) {
      const depth = n.node_path.length;
      if (!byDepth.has(depth)) byDepth.set(depth, []);
      byDepth.get(depth)!.push(n);
    }

    return nodes.map((n) => {
      const depth = n.node_path.length;
      const siblings = byDepth.get(depth) ?? [];
      const idx = siblings.indexOf(n);
      const xSpacing = 220;
      const ySpacing = 120;
      const xOffset = (siblings.length - 1) * xSpacing * -0.5;
      const color = DEPTH_COLORS[Math.min(depth, DEPTH_COLORS.length - 1)];

      return {
        id: n.id,
        type: "default",
        position: { x: xOffset + idx * xSpacing, y: depth * ySpacing },
        data: {
          label: n.label,
          nodePath: n.node_path,
        },
        style: {
          background: color,
          color: depth <= 2 ? "#fff" : "#1e293b",
          border: "none",
          borderRadius: "8px",
          padding: "8px 16px",
          fontSize: "13px",
          fontWeight: 500,
        },
      };
    });
  }, [nodes]);

  const flowEdges: Edge[] = useMemo(
    () =>
      edges.map((e, i) => {
        const isCrossRef = e.edge_type === "cross_ref";
        const label = isCrossRef
          ? RELATION_LABELS[e.relation_type ?? ""] ?? e.relation_type ?? "关联"
          : undefined;
        return {
          id: e.id || `e-${i}`,
          source: e.source,
          target: e.target,
          animated: isCrossRef,
          style: isCrossRef
            ? { stroke: "#3b82f6", strokeDasharray: "5 5", cursor: "pointer" }
            : { stroke: "#94a3b8" },
          label,
          labelStyle: isCrossRef ? { fontSize: 11, fill: "#3b82f6" } : undefined,
        };
      }),
    [edges],
  );

  const handleEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: Edge) => {
      if (!onEdgeClick) return;
      const original = edges.find((e) => (e.id || "") === edge.id);
      if (original && original.edge_type === "cross_ref") {
        onEdgeClick(edge.id, original);
      }
    },
    [onEdgeClick, edges],
  );

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      router.push(`/projects/${projectId}/wiki/${node.id}`);
    },
    [router, projectId],
  );

  return (
    <ReactFlow
      nodes={flowNodes}
      edges={flowEdges}
      onNodeClick={onNodeClick}
      onEdgeClick={handleEdgeClick}
      fitView
      minZoom={0.2}
      maxZoom={2}
    >
      <MiniMap
        nodeColor={// eslint-disable-next-line @typescript-eslint/no-explicit-any
          (n: any) => (n.style?.background as string) ?? "#3b82f6"}
        maskColor="rgba(0,0,0,0.1)"
      />
      <Controls />
      <Background gap={16} size={1} />
    </ReactFlow>
  );
}
