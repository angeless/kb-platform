"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";

interface Project {
  id: string;
  name: string;
  industry_hint: string | null;
  status: string;
}

export default function ProjectSettingsPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchProject = async () => {
      try {
        const resp = await api.get<Project>(`/v1/projects/${projectId}`);
        setProject(resp.data);
        setName(resp.data.name);
        setIndustry(resp.data.industry_hint || "");
      } catch (e) {
        setError(e instanceof ApiClientError ? e.message : "加载失败");
      }
    };
    fetchProject();
  }, [projectId]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage("");
    setError("");
    try {
      await api.patch(`/v1/projects/${projectId}`, {
        name,
        industry_hint: industry || null,
      });
      setMessage("保存成功");
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await api.del(`/v1/projects/${projectId}`);
      router.push("/projects");
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "删除失败");
      setDeleting(false);
    }
  };

  if (!project && !error) {
    return <div className="py-12 text-center text-gray-400">加载中...</div>;
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <Link href={`/projects/${projectId}`} className="text-sm text-primary-600 hover:underline">
          ← 返回项目
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-gray-900">项目设置</h1>
      </div>

      {message && (
        <div className="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-600">{message}</div>
      )}
      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>
      )}

      {/* Basic Settings */}
      <div className="mb-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold">基本信息</h2>
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">项目名称</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">行业</label>
            <input
              type="text"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              placeholder="可选"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {saving ? "保存中..." : "保存"}
          </button>
        </form>
      </div>

      {/* Danger Zone */}
      <div className="rounded-xl border border-red-200 bg-white p-6 shadow-sm">
        <h2 className="mb-2 text-lg font-semibold text-red-600">危险区域</h2>
        <p className="mb-4 text-sm text-gray-500">删除项目后，所有资料、文档、架构将不可恢复。</p>
        {!confirmDelete ? (
          <button
            onClick={() => setConfirmDelete(true)}
            className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
          >
            删除项目
          </button>
        ) : (
          <div className="flex items-center gap-3">
            <span className="text-sm text-red-600">确认删除？此操作不可撤销。</span>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
            >
              {deleting ? "删除中..." : "确认删除"}
            </button>
            <button
              onClick={() => setConfirmDelete(false)}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              取消
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
