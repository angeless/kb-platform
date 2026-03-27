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
  node_name: string;
  node_path: string[];
  doc_count: number;
}

interface GraphEdge {
  source: string;
  target: string;
  rel_type: string;
}

interface KnowledgeGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  projectId: string;
}

const DEPTH_COLORS = ["#1e40af", "#3b82f6", "#60a5fa", "#93c5fd", "#bfdbfe"];

export default function KnowledgeGraph({ nodes, edges, projectId }: KnowledgeGraphProps) {
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
          label: n.node_name,
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
        const isCrossRef = e.rel_type === "cross_ref";
        return {
          id: `e-${i}`,
          source: e.source,
          target: e.target,
          animated: isCrossRef,
          style: isCrossRef
            ? { stroke: "#3b82f6", strokeDasharray: "5 5" }
            : { stroke: "#94a3b8" },
          label: isCrossRef ? "cross_ref" : undefined,
        };
      }),
    [edges],
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
      fitView
      minZoom={0.2}
      maxZoom={2}
    >
      <MiniMap
        nodeColor={(n) => (n.style?.background as string) ?? "#3b82f6"}
        maskColor="rgba(0,0,0,0.1)"
      />
      <Controls />
      <Background gap={16} size={1} />
    </ReactFlow>
  );
}
