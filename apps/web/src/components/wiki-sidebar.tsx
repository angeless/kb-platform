"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { api } from "@/lib/api";

interface ArchNode {
  id: string;
  node_name: string;
  node_type: string;
  level: number;
  description: string | null;
  parent_id: string | null;
}

interface DocItem {
  id: string;
  title: string;
  node_id: string | null;
  doc_type: string;
  status: string;
}

interface TreeItem {
  node: ArchNode;
  children: TreeItem[];
  docs: DocItem[];
}

interface WikiSidebarProps {
  projectId: string;
  collapsed?: boolean;
  onToggle?: () => void;
}

function buildNodeTree(nodes: ArchNode[]): TreeItem[] {
  const map = new Map<string, TreeItem>();
  const roots: TreeItem[] = [];
  for (const n of nodes) {
    map.set(n.id, { node: n, children: [], docs: [] });
  }
  for (const n of nodes) {
    const item = map.get(n.id)!;
    if (n.parent_id && map.has(n.parent_id)) {
      map.get(n.parent_id)!.children.push(item);
    } else {
      roots.push(item);
    }
  }
  return roots;
}

function attachDocs(tree: TreeItem[], docs: DocItem[]) {
  const nodeMap = new Map<string, TreeItem>();
  const collectNodes = (items: TreeItem[]) => {
    for (const item of items) {
      nodeMap.set(item.node.id, item);
      collectNodes(item.children);
    }
  };
  collectNodes(tree);
  for (const doc of docs) {
    if (doc.node_id && nodeMap.has(doc.node_id)) {
      nodeMap.get(doc.node_id)!.docs.push(doc);
    }
  }
}

function NavItem({
  item,
  projectId,
  depth,
  expandedIds,
  toggleExpand,
  searchQuery,
  currentDocId,
}: {
  item: TreeItem;
  projectId: string;
  depth: number;
  expandedIds: Set<string>;
  toggleExpand: (id: string) => void;
  searchQuery: string;
  currentDocId: string | null;
}) {
  const isExpanded = expandedIds.has(item.node.id);
  const hasChildren = item.children.length > 0 || item.docs.length > 0;

  // Filter by search
  const matchesSearch = (text: string) =>
    !searchQuery || text.toLowerCase().includes(searchQuery.toLowerCase());

  const filteredDocs = item.docs.filter((d) => matchesSearch(d.title));
  const hasMatchingContent =
    matchesSearch(item.node.node_name) ||
    filteredDocs.length > 0 ||
    item.children.some((c) => matchesSearch(c.node.node_name));

  if (searchQuery && !hasMatchingContent) return null;

  return (
    <div>
      {/* Node row */}
      <button
        onClick={() => hasChildren && toggleExpand(item.node.id)}
        className={`flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-left text-sm transition-colors ${
          isExpanded ? "text-white" : "text-slate-300"
        } hover:bg-slate-800`}
        style={{ paddingLeft: `${depth * 16 + 12}px` }}
      >
        {hasChildren ? (
          <span className="w-4 shrink-0 text-xs text-slate-500">
            {isExpanded ? "▾" : "▸"}
          </span>
        ) : (
          <span className="w-4 shrink-0" />
        )}
        <span className="truncate font-medium">{item.node.node_name}</span>
        {item.docs.length > 0 && (
          <span className="ml-auto shrink-0 text-xs text-slate-500">
            {item.docs.length}
          </span>
        )}
      </button>

      {/* Expanded children */}
      {(isExpanded || searchQuery) && (
        <>
          {item.children.map((child) => (
            <NavItem
              key={child.node.id}
              item={child}
              projectId={projectId}
              depth={depth + 1}
              expandedIds={expandedIds}
              toggleExpand={toggleExpand}
              searchQuery={searchQuery}
              currentDocId={currentDocId}
            />
          ))}

          {/* Docs under this node */}
          {(searchQuery ? filteredDocs : item.docs).map((doc) => (
            <Link
              key={doc.id}
              href={`/projects/${projectId}/wiki/${doc.id}`}
              className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors ${
                currentDocId === doc.id
                  ? "bg-teal-600 font-medium text-white"
                  : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              }`}
              style={{ paddingLeft: `${(depth + 1) * 16 + 12}px` }}
            >
              <span className="w-4 shrink-0 text-xs">📄</span>
              <span className="truncate">{doc.title}</span>
            </Link>
          ))}
        </>
      )}
    </div>
  );
}

export function WikiSidebar({ projectId, collapsed, onToggle }: WikiSidebarProps) {
  const pathname = usePathname();
  const [tree, setTree] = useState<TreeItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  // Extract current doc id from URL
  const currentDocId = pathname.match(/\/wiki\/([^/]+)/)?.[1] || null;

  const toggleExpand = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  useEffect(() => {
    const load = async () => {
      try {
        // Load architecture
        const archResp = await api.get<{ id: string; status: string }[]>(
          `/v1/projects/${projectId}/architectures`,
        );
        const archs = archResp.data;
        const published = archs.find((a) => a.status === "published") || archs[0];

        if (!published) { setIsLoading(false); return; }

        // Load nodes and docs in parallel
        const [nodesResp, docsResp] = await Promise.all([
          api.get<ArchNode[]>(`/v1/architectures/${published.id}/nodes`),
          api.get<DocItem[]>(`/v1/docs?project_id=${projectId}&page=1&page_size=200`),
        ]);

        const nodeTree = buildNodeTree(nodesResp.data);
        attachDocs(nodeTree, docsResp.data);
        setTree(nodeTree);

        // Auto-expand first level
        const topIds = new Set(nodesResp.data.filter((n) => !n.parent_id).map((n) => n.id));
        setExpandedIds(topIds);
      } catch {
        // Sidebar data is non-critical
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [projectId]);

  if (collapsed) {
    return (
      <aside className="flex h-full w-12 flex-col items-center border-r border-slate-800 bg-slate-900 py-4">
        <button
          onClick={onToggle}
          className="rounded-md p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
          aria-label="展开导航"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </aside>
    );
  }

  return (
    <aside className="flex h-full w-64 flex-col bg-slate-900">
      {/* Header */}
      <div className="sticky top-0 z-10 border-b border-slate-800 bg-slate-900 px-4 py-3">
        <div className="flex items-center justify-between">
          <Link
            href={`/projects/${projectId}/wiki`}
            className="text-sm font-bold text-white hover:text-teal-400"
          >
            知识 Wiki
          </Link>
          {onToggle && (
            <button
              onClick={onToggle}
              className="rounded p-1 text-slate-500 hover:bg-slate-800 hover:text-white"
              aria-label="收起导航"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
          )}
        </div>

        {/* Search box */}
        <div className="mt-3">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索知识库..."
            className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
          />
        </div>
      </div>

      {/* Navigation tree */}
      <nav className="flex-1 overflow-y-auto px-2 py-2">
        {isLoading ? (
          <div className="px-3 py-4 text-xs text-slate-500">加载架构树...</div>
        ) : tree.length === 0 ? (
          <div className="px-3 py-4 text-xs text-slate-500">
            暂无架构树。
            <Link href={`/projects/${projectId}/architectures`} className="text-teal-400 hover:underline">
              去创建
            </Link>
          </div>
        ) : (
          tree.map((item) => (
            <NavItem
              key={item.node.id}
              item={item}
              projectId={projectId}
              depth={0}
              expandedIds={expandedIds}
              toggleExpand={toggleExpand}
              searchQuery={searchQuery}
              currentDocId={currentDocId}
            />
          ))
        )}
      </nav>

      {/* Footer with search page link */}
      <div className="border-t border-slate-800 px-4 py-3">
        <Link
          href={`/projects/${projectId}/wiki/search`}
          className="flex items-center gap-2 text-xs text-slate-500 hover:text-teal-400"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          高级搜索（语义 + 全文）
        </Link>
      </div>
    </aside>
  );
}
