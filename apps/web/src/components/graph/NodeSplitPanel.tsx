"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiClientError } from "@/lib/api";
import { showErrorToast } from "@/components/error-toast";

interface DocItem {
  id: string;
  title: string;
}

interface NodeSplitPanelProps {
  projectId: string;
  nodeId: string;
  nodeName: string;
  onClose: () => void;
  onSuccess: () => void;
}

export function NodeSplitPanel({
  projectId,
  nodeId,
  nodeName,
  onClose,
  onSuccess,
}: NodeSplitPanelProps) {
  const [docs, setDocs] = useState<DocItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [nameA, setNameA] = useState("");
  const [nameB, setNameB] = useState("");
  // Track which group each doc belongs to: "a" or "b"
  const [assignment, setAssignment] = useState<Record<string, "a" | "b">>({});

  const fetchDocs = useCallback(async () => {
    try {
      const resp = await api.get<DocItem[]>(
        `/v1/docs?project_id=${projectId}&node_id=${nodeId}&page_size=200`,
      );
      const items = resp.data ?? [];
      setDocs(items);
      // Default all to group A
      const initial: Record<string, "a" | "b"> = {};
      items.forEach((d) => { initial[d.id] = "a"; });
      setAssignment(initial);
    } catch {
      showErrorToast("加载文档列表失败");
    } finally {
      setLoading(false);
    }
  }, [projectId, nodeId]);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  const toggleDoc = (docId: string) => {
    setAssignment((prev) => ({
      ...prev,
      [docId]: prev[docId] === "a" ? "b" : "a",
    }));
  };

  const groupA = docs.filter((d) => assignment[d.id] === "a");
  const groupB = docs.filter((d) => assignment[d.id] === "b");

  const canSubmit = nameA.trim() && nameB.trim() && groupA.length > 0 && groupB.length > 0;

  const handleSplit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      await api.post(`/v1/projects/${projectId}/graph/nodes/${nodeId}/split`, {
        part_a: {
          name: nameA.trim(),
          node_type: "topic",
          doc_ids: groupA.map((d) => d.id),
        },
        part_b: {
          name: nameB.trim(),
          node_type: "topic",
          doc_ids: groupB.map((d) => d.id),
        },
      });
      showErrorToast(`已将"${nodeName}"拆分为"${nameA.trim()}"和"${nameB.trim()}"`, "info");
      onSuccess();
    } catch (e) {
      showErrorToast(e instanceof ApiClientError ? e.message : "拆分失败");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex w-96 flex-col border-l border-gray-200 bg-white shadow-xl">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
        <h3 className="text-lg font-semibold text-gray-900">拆分分类</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
          ✕
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <p className="mb-3 text-sm text-gray-500">
          将"{nodeName}"下的文档分配到两个新分类中。点击文档切换分组。
        </p>

        {/* Name inputs */}
        <div className="mb-4 grid grid-cols-2 gap-2">
          <div>
            <label className="mb-1 block text-xs font-medium text-blue-600">分类 A 名称</label>
            <input
              type="text"
              value={nameA}
              onChange={(e) => setNameA(e.target.value)}
              placeholder="分类 A"
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-primary-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-amber-600">分类 B 名称</label>
            <input
              type="text"
              value={nameB}
              onChange={(e) => setNameB(e.target.value)}
              placeholder="分类 B"
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-primary-500 focus:outline-none"
            />
          </div>
        </div>

        {loading ? (
          <div className="py-8 text-center text-sm text-gray-400">加载文档列表...</div>
        ) : docs.length === 0 ? (
          <div className="py-8 text-center text-sm text-gray-400">该分类下没有文档</div>
        ) : (
          <div className="space-y-1.5">
            {docs.map((doc) => {
              const group = assignment[doc.id];
              return (
                <button
                  key={doc.id}
                  onClick={() => toggleDoc(doc.id)}
                  className={`w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                    group === "a"
                      ? "border border-blue-200 bg-blue-50 text-blue-800"
                      : "border border-amber-200 bg-amber-50 text-amber-800"
                  }`}
                >
                  <span className="mr-2 text-xs font-bold">
                    {group === "a" ? "A" : "B"}
                  </span>
                  {doc.title}
                </button>
              );
            })}
          </div>
        )}

        {/* Summary */}
        {docs.length > 0 && (
          <div className="mt-3 flex gap-2 text-xs text-gray-500">
            <span className="text-blue-600">A: {groupA.length} 个</span>
            <span className="text-amber-600">B: {groupB.length} 个</span>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-gray-200 p-4">
        <button
          onClick={handleSplit}
          disabled={!canSubmit || submitting}
          className="w-full rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          {submitting ? "拆分中..." : "确认拆分"}
        </button>
      </div>
    </div>
  );
}
