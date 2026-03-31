"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";
import { PermissionGuard } from "@/components/PermissionGuard";

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
  const [docTotal, setDocTotal] = useState<number | null>(null);
  const [archTotal, setArchTotal] = useState<number | null>(null);
  const [jobTotal, setJobTotal] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // Knowledge insights
  const [discoveringPatterns, setDiscoveringPatterns] = useState(false);
  const [patterns, setPatterns] = useState<{
    clusters: Array<{ theme: string; doc_ids: string[]; keywords: string[] }>;
    frequent_associations: Array<{ entity_a: string; entity_b: string; co_occurrence: number }>;
    knowledge_gaps: string[];
    analyzed_docs_count: number;
  } | null>(null);
  const [contradictionCount, setContradictionCount] = useState<number | null>(null);
  const [insightError, setInsightError] = useState("");

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        const [projResp, assetsResp, docsResp, archResp, jobsResp] = await Promise.all([
          api.get<Project>(`/v1/projects/${projectId}`),
          api.get<AssetSummary[]>(`/v1/assets?project_id=${projectId}&page_size=5`),
          api.get<unknown[]>(`/v1/docs?project_id=${projectId}&page=1&page_size=1`).catch(() => null),
          api.get<unknown[]>(`/v1/projects/${projectId}/architectures`).catch(() => null),
          api.get<unknown[]>(`/v1/jobs?project_id=${projectId}&page=1&page_size=1`).catch(() => null),
        ]);
        setProject(projResp.data);
        setAssets(assetsResp.data);
        setAssetTotal(assetsResp.meta?.total ?? 0);
        if (docsResp) setDocTotal(docsResp.meta?.total ?? docsResp.data?.length ?? 0);
        if (archResp) setArchTotal(archResp.data?.length ?? 0);
        if (jobsResp) setJobTotal(jobsResp.meta?.total ?? jobsResp.data?.length ?? 0);

        // Fetch contradiction count (cross-refs with type=contradicts)
        try {
          const crossRefsResp = await api.get<unknown[]>(
            `/v1/cross-refs?project_id=${projectId}&relation_type=contradicts&page_size=1`,
          );
          setContradictionCount(crossRefsResp.meta?.total ?? 0);
        } catch {
          // Non-critical
        }
      } catch (e) {
        setError(e instanceof ApiClientError ? e.message : "加载失败");
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [projectId]);

  const handleDiscoverPatterns = async () => {
    setDiscoveringPatterns(true);
    setInsightError("");
    try {
      const resp = await api.post<{
        clusters: Array<{ theme: string; doc_ids: string[]; keywords: string[] }>;
        frequent_associations: Array<{ entity_a: string; entity_b: string; co_occurrence: number }>;
        knowledge_gaps: string[];
        analyzed_docs_count: number;
      }>(`/v1/projects/${projectId}/ai-discover-patterns`, {});
      setPatterns(resp.data);
    } catch (e) {
      setInsightError(e instanceof ApiClientError ? e.message : "模式发现失败");
    } finally {
      setDiscoveringPatterns(false);
    }
  };

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
      <div className="mb-6 grid grid-cols-4 gap-3 lg:grid-cols-8">
        {[
          { label: "资料", count: assetTotal, href: `/projects/${projectId}/assets` },
          { label: "文档", count: docTotal ?? "—", href: `/projects/${projectId}/docs` },
          { label: "架构", count: archTotal ?? "—", href: `/projects/${projectId}/architectures` },
          { label: "任务", count: jobTotal ?? "—", href: `/projects/${projectId}/jobs` },
          { label: "检索", count: "→", href: `/projects/${projectId}/search` },
          { label: "Wiki", count: "→", href: `/projects/${projectId}/wiki` },
          { label: "图谱", count: "→", href: `/projects/${projectId}/graph` },
          { label: "问答", count: "→", href: `/projects/${projectId}/qa` },
          { label: "冲突", count: "→", href: `/projects/${projectId}/conflicts` },
          { label: "导出", count: "→", href: `/projects/${projectId}/exports` },
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

      {/* Knowledge Insights */}
      <PermissionGuard action="edit">
        <div className="mb-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">知识洞察</h2>
            <button
              onClick={handleDiscoverPatterns}
              disabled={discoveringPatterns}
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              {discoveringPatterns ? "分析中..." : "发现模式"}
            </button>
          </div>

          {/* Contradiction stats */}
          {contradictionCount !== null && (
            <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-50 px-4 py-2.5">
              <span className="text-sm font-medium text-red-700">已检测矛盾</span>
              <span className="rounded-full bg-red-100 px-2 py-0.5 text-sm font-bold text-red-700">
                {contradictionCount}
              </span>
              <Link
                href={`/projects/${projectId}/graph`}
                className="ml-auto text-xs text-red-600 hover:underline"
              >
                在图谱中查看 →
              </Link>
            </div>
          )}

          {insightError && (
            <div className="mb-3 rounded-lg bg-red-50 p-3 text-sm text-red-600">{insightError}</div>
          )}

          {patterns && (
            <div className="space-y-4">
              {/* Clusters */}
              {patterns.clusters.length > 0 && (
                <div>
                  <h3 className="mb-2 text-sm font-medium text-gray-700">主题聚类</h3>
                  <div className="space-y-2">
                    {patterns.clusters.slice(0, 5).map((c, i) => (
                      <div key={i} className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-gray-900">{c.theme}</span>
                          <span className="text-xs text-gray-400">{c.doc_ids.length} 篇文档</span>
                        </div>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {c.keywords.slice(0, 5).map((kw) => (
                            <span key={kw} className="rounded-full bg-primary-50 px-2 py-0.5 text-xs text-primary-700">
                              {kw}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Frequent associations */}
              {patterns.frequent_associations.length > 0 && (
                <div>
                  <h3 className="mb-2 text-sm font-medium text-gray-700">高频关联</h3>
                  <div className="space-y-1">
                    {patterns.frequent_associations.slice(0, 10).map((a, i) => (
                      <div key={i} className="flex items-center gap-2 text-sm">
                        <span className="text-gray-700">{a.entity_a}</span>
                        <span className="text-xs text-gray-400">↔</span>
                        <span className="text-gray-700">{a.entity_b}</span>
                        <span className="ml-auto text-xs text-gray-400">共现 {a.co_occurrence} 次</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Knowledge gaps */}
              {patterns.knowledge_gaps.length > 0 && (
                <div>
                  <h3 className="mb-2 text-sm font-medium text-gray-700">知识缺口</h3>
                  <ul className="space-y-1">
                    {patterns.knowledge_gaps.map((gap, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                        <span className="mt-0.5 text-amber-500">⚠</span>
                        {gap}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <p className="text-xs text-gray-400">
                分析了 {patterns.analyzed_docs_count} 篇文档
              </p>
            </div>
          )}

          {!patterns && !insightError && !discoveringPatterns && (
            <p className="text-sm text-gray-400">点击"发现模式"开始 AI 分析项目知识结构</p>
          )}
        </div>
      </PermissionGuard>

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
          <div className="px-5 py-10 text-center">
            <div className="mb-3 text-3xl">📄</div>
            <p className="mb-3 text-gray-500">还没有上传任何资料</p>
            <Link
              href={`/projects/${projectId}/assets`}
              className="inline-block rounded-lg bg-primary-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-primary-700"
            >
              上传第一份资料
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
