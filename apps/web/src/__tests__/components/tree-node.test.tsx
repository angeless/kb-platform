import { describe, it, expect } from "vitest";
import { buildTree, type TreeNodeData } from "@/components/tree-node";

describe("buildTree", () => {
  it("builds tree from flat list", () => {
    const nodes: TreeNodeData[] = [
      { id: "1", node_name: "Root", node_type: "category", level: 0, description: null, status: "active", parent_id: null, children: [] },
      { id: "2", node_name: "Child", node_type: "topic", level: 1, description: null, status: "draft", parent_id: "1", children: [] },
      { id: "3", node_name: "Sibling", node_type: "topic", level: 1, description: null, status: "draft", parent_id: "1", children: [] },
    ];

    const tree = buildTree(nodes);
    expect(tree).toHaveLength(1);
    expect(tree[0].node_name).toBe("Root");
    expect(tree[0].children).toHaveLength(2);
    expect(tree[0].children[0].node_name).toBe("Child");
  });

  it("handles empty list", () => {
    expect(buildTree([])).toEqual([]);
  });

  it("handles orphan nodes as roots", () => {
    const nodes: TreeNodeData[] = [
      { id: "1", node_name: "Orphan", node_type: "topic", level: 0, description: null, status: "active", parent_id: "nonexistent", children: [] },
    ];

    const tree = buildTree(nodes);
    expect(tree).toHaveLength(1);
    expect(tree[0].node_name).toBe("Orphan");
  });
});
