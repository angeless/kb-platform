"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, ApiClientError } from "@/lib/api";
import { MarkdownView } from "@/components/markdown-view";

interface DocDetail {
  id: string;
  title: string;
  status: string;
  current_version: number;
  versions: { version: number; content_md: string }[];
}

export default function DocEditPage() {
  const params = useParams();
  const router = useRouter();
  const docId = params.id as string;

  const [content, setContent] = useState("");
  const [reason, setReason] = useState("");
  const [preview, setPreview] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  // Track original content to detect unsaved changes
  const initialContentRef = useRef("");

  useEffect(() => {
    const fetch = async () => {
      try {
        const resp = await api.get<DocDetail>(`/v1/docs/${docId}`);
        if (resp.data.status !== "draft") {
          setError("只有草稿状态的文档可以编辑");
          return;
        }
        const latest = resp.data.versions.sort((a, b) => b.version - a.version)[0];
        if (latest) {
          setContent(latest.content_md);
          initialContentRef.current = latest.content_md;
        }
      } catch (e) {
        setError(e instanceof ApiClientError ? e.message : "加载失败");
      } finally {
        setIsLoading(false);
      }
    };
    fetch();
  }, [docId]);

  // Warn user before leaving with unsaved changes
  const isDirty = content !== initialContentRef.current;

  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (content !== initialContentRef.current) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [content]);

  const handleSave = async () => {
    if (!content.trim() || !reason.trim()) {
      setError("内容和变更原因不能为空");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await api.put(`/v1/docs/${docId}/content`, {
        content_md: content,
        change_reason: reason,
      });
      // Clear dirty mark so navigation doesn't trigger warning
      initialContentRef.current = content;
      router.push(`/docs/${docId}`);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const handleNavigateBack = useCallback(() => {
    if (content !== initialContentRef.current) {
      if (!window.confirm("有未保存的修改，确定离开吗？")) return;
    }
    router.push(`/docs/${docId}`);
  }, [content, docId, router]);

  if (isLoading) return <div className="py-12 text-center text-gray-400">加载中...</div>;

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-4">
        <button onClick={handleNavigateBack} className="text-sm text-primary-600 hover:underline">
          ← 返回文档
        </button>
      </div>

      <h1 className="mb-6 text-2xl font-bold text-gray-900">编辑文档</h1>

      {error && <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

      {/* Toggle */}
      <div className="mb-3 flex gap-2">
        <button
          onClick={() => setPreview(false)}
          className={`rounded-lg px-3 py-1.5 text-sm ${!preview ? "bg-primary-100 text-primary-700" : "text-gray-500"}`}
        >
          编辑
        </button>
        <button
          onClick={() => setPreview(true)}
          className={`rounded-lg px-3 py-1.5 text-sm ${preview ? "bg-primary-100 text-primary-700" : "text-gray-500"}`}
        >
          预览
        </button>
      </div>

      {/* Editor / Preview */}
      {preview ? (
        <div className="min-h-[400px] rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <MarkdownView content={content} />
        </div>
      ) : (
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={20}
          className="w-full rounded-xl border border-gray-300 bg-white p-4 font-mono text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          placeholder="使用 Markdown 格式编写文档内容..."
        />
      )}

      {/* Change Reason */}
      <div className="mt-4">
        <label className="mb-1 block text-sm font-medium text-gray-700">变更原因</label>
        <input
          type="text"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="描述本次修改的原因"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
        />
      </div>

      <div className="mt-4 flex gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded-lg bg-primary-600 px-6 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          {saving ? "保存中..." : "保存新版本"}
        </button>
        <button onClick={handleNavigateBack} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">
          取消
        </button>
      </div>
    </div>
  );
}
