"use client";

import { useEffect, useState } from "react";
import { api, ApiClientError } from "@/lib/api";

interface Project {
  id: string;
  name: string;
  industry_hint: string | null;
  status: string;
  created_at: string;
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // Create project form
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newIndustry, setNewIndustry] = useState("");
  const [creating, setCreating] = useState(false);

  const fetchProjects = async () => {
    setIsLoading(true);
    try {
      const resp = await api.get<Project[]>("/v1/projects?page=1&page_size=50");
      setProjects(resp.data);
      setTotal(resp.meta?.total ?? resp.data.length);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "加载项目失败");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await api.post("/v1/projects", {
        name: newName,
        industry_hint: newIndustry || null,
      });
      setNewName("");
      setNewIndustry("");
      setShowCreate(false);
      await fetchProjects();
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "创建失败");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">项目列表</h1>
          <p className="mt-1 text-sm text-gray-500">共 {total} 个项目</p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          新建项目
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {showCreate && (
        <div className="mb-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-medium">新建项目</h3>
          <form onSubmit={handleCreate} className="flex gap-4">
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="项目名称"
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
            <input
              type="text"
              value={newIndustry}
              onChange={(e) => setNewIndustry(e.target.value)}
              placeholder="行业（可选）"
              className="w-40 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
            <button
              type="submit"
              disabled={creating}
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              {creating ? "创建中..." : "创建"}
            </button>
          </form>
        </div>
      )}

      {isLoading ? (
        <div className="py-12 text-center text-gray-400">加载中...</div>
      ) : projects.length === 0 ? (
        <div className="py-12 text-center">
          <p className="text-gray-400">还没有项目</p>
          <p className="mt-1 text-sm text-gray-400">
            点击"新建项目"开始构建知识系统
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <div
              key={project.id}
              className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md"
            >
              <div className="mb-3 flex items-start justify-between">
                <h3 className="font-semibold text-gray-900">{project.name}</h3>
                <span className="rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
                  {project.status}
                </span>
              </div>
              {project.industry_hint && (
                <p className="mb-2 text-sm text-gray-500">
                  行业：{project.industry_hint}
                </p>
              )}
              <p className="text-xs text-gray-400">
                创建于 {new Date(project.created_at).toLocaleDateString("zh-CN")}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
