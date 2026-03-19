"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

interface Project {
  id: string;
  name: string;
  industry_hint: string | null;
  status: string;
  created_at: string;
}

interface AssetSummary {
  id: string;
  filename: string;
  asset_type: string;
  parse_status: string;
  uploaded_at: string;
}

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [assets, setAssets] = useState<AssetSummary[]>([]);
  const [assetTotal, setAssetTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        const [projResp, assetsResp] = await Promise.all([
          api.get<Project>(`/v1/projects/${projectId}`),
          api.get<AssetSummary[]>(`/v1/assets?project_id=${projectId}&page_size=5`),
        ]);
        setProject(projResp.data);
        setAssets(assetsResp.data);
        setAssetTotal(assetsResp.meta?.total ?? 0);
      } catch (e) {
        setError(e instanceof ApiClientError ? e.message : "加载失败");
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [projectId]);

  if (isLoading) {
    return <div className="py-12 text-center text-gray-400">加载中...</div>;
  }

  if (error || !project) {
    return (
      <div className="py-12 text-center text-red-500">{error || "项目不存在"}</div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
            <StatusBadge status={project.status} />
          </div>
          {project.industry_hint && (
            <p className="mt-1 text-sm text-gray-500">行业：{project.industry_hint}</p>
          )}
        </div>
        <Link
          href={`/projects/${projectId}/settings`}
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
        >
          项目设置
        </Link>
      </div>

      {/* Quick Stats */}
      <div className="mb-6 grid grid-cols-4 gap-3 lg:grid-cols-7">
        {[
          { label: "资料", count: assetTotal, href: `/projects/${projectId}/assets` },
          { label: "文档", count: "—", href: `/projects/${projectId}/docs` },
          { label: "架构", count: "—", href: `/projects/${projectId}/architectures` },
          { label: "任务", count: "—", href: `/projects/${projectId}/jobs` },
          { label: "检索", count: "—", href: `/projects/${projectId}/search` },
          { label: "冲突", count: "—", href: `/projects/${projectId}/conflicts` },
          { label: "导出", count: "—", href: `/projects/${projectId}/exports` },
        ].map((stat) => (
          <Link
            key={stat.label}
            href={stat.href}
            className="rounded-xl border border-gray-200 bg-white p-4 text-center shadow-sm transition-shadow hover:shadow-md"
          >
            <div className="text-2xl font-bold text-primary-600">{stat.count}</div>
            <div className="mt-1 text-sm text-gray-500">{stat.label}</div>
          </Link>
        ))}
      </div>

      {/* Recent Assets */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-gray-200 px-5 py-4">
          <h2 className="font-semibold text-gray-900">最近资料</h2>
          <Link
            href={`/projects/${projectId}/assets`}
            className="text-sm text-primary-600 hover:underline"
          >
            查看全部 →
          </Link>
        </div>
        {assets.length === 0 ? (
          <div className="px-5 py-8 text-center text-gray-400">
            还没有资料，
            <Link href={`/projects/${projectId}/assets`} className="text-primary-600 hover:underline">
              去上传
            </Link>
          </div>
        ) : (
          <ul>
            {assets.map((asset) => (
              <li key={asset.id} className="flex items-center justify-between border-b border-gray-100 px-5 py-3 last:border-0">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-gray-900">{asset.filename}</span>
                  <span className="text-xs text-gray-400">{asset.asset_type}</span>
                </div>
                <StatusBadge status={asset.parse_status} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
